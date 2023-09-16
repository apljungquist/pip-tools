from __future__ import annotations

import collections
import contextlib
import os
import pathlib
import sys
import tempfile
from dataclasses import dataclass
from importlib import metadata as importlib_metadata
from typing import Any, Iterator, Protocol, TypeVar, overload

import build
import build.env
import pyproject_hooks
from pip._internal.req import InstallRequirement
from pip._internal.req.constructors import install_req_from_line, parse_req_from_line

PYPROJECT_TOML = "pyproject.toml"

_T = TypeVar("_T")


if sys.version_info >= (3, 10):
    from importlib.metadata import PackageMetadata
else:

    class PackageMetadata(Protocol):
        @overload
        def get_all(self, name: str, failobj: None = None) -> list[Any] | None:
            ...

        @overload
        def get_all(self, name: str, failobj: _T) -> list[Any] | _T:
            ...


@dataclass
class ProjectMetadata:
    extras: tuple[str, ...]
    requirements: tuple[InstallRequirement, ...]
    build_requirements: tuple[InstallRequirement, ...]


def build_project_metadata(
    src_file: str,
    build_distributions: tuple[str, ...],
    *,
    isolated: bool,
    quiet: bool,
) -> ProjectMetadata:
    """
    Return the metadata for a project.

    Uses the ``prepare_metadata_for_build_wheel`` hook for the wheel metadata
    if available, otherwise ``build_wheel``.

    Uses the ``prepare_metadata_for_build_{dist}`` hook for each ``build_distributions``
    if available.

    :param src_file: Project source file
    :param build_distributions: A tuple of build distributions to get the dependencies
                                of (``sdist`` or ``wheel`` or ``editable``).
    :param isolated: Whether to run invoke the backend in the current
                     environment or to create an isolated one and invoke it
                     there.
    :param quiet: Whether to suppress the output of subprocesses.
    """

    src_dir = os.path.dirname(os.path.abspath(src_file))
    with _create_project_builder(src_dir, isolated=isolated, quiet=quiet) as builder:
        metadata = _build_project_wheel_metadata(builder)
        extras = tuple(metadata.get_all("Provides-Extra") or ())
        requirements = tuple(
            _prepare_requirements(metadata=metadata, src_file=src_file)
        )
        build_requirements = tuple(
            _prepare_build_requirements(
                builder=builder,
                src_file=src_file,
                distributions=build_distributions,
                package_name=_get_name(metadata),
            )
        )
        return ProjectMetadata(
            extras=extras,
            requirements=requirements,
            build_requirements=build_requirements,
        )


@contextlib.contextmanager
def _create_project_builder(
    src_dir: str, *, isolated: bool, quiet: bool
) -> Iterator[build.ProjectBuilder]:
    builder = build.ProjectBuilder(
        os.fspath(src_dir),
        runner=pyproject_hooks.quiet_subprocess_runner
        if quiet
        else pyproject_hooks.default_subprocess_runner,
    )

    if not isolated:
        yield builder
        return

    with build.env.IsolatedEnvBuilder() as env:
        builder.python_executable = env.executable
        builder.scripts_dir = env.scripts_dir
        env.install(builder.build_system_requires)
        env.install(builder.get_requires_for_build("wheel"))
        yield builder


def _build_project_wheel_metadata(
    builder: build.ProjectBuilder,
) -> PackageMetadata:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = pathlib.Path(builder.metadata_path(tmpdir))
        return importlib_metadata.PathDistribution(path).metadata


def _get_name(metadata: PackageMetadata) -> str:
    return metadata.get_all("Name")[0]  # type: ignore


def _prepare_requirements(
    metadata: PackageMetadata, src_file: str
) -> Iterator[InstallRequirement]:
    package_name = _get_name(metadata)
    comes_from = f"{package_name} ({src_file})"

    for req in metadata.get_all("Requires-Dist") or []:
        parts = parse_req_from_line(req, comes_from)
        if parts.requirement.name == package_name:
            package_dir = os.path.dirname(os.path.abspath(src_file))
            # Replace package name with package directory in the requirement
            # string so that pip can find the package as self-referential.
            # Note the string can contain extras, so we need to replace only
            # the package name, not the whole string.
            replaced_package_name = req.replace(package_name, package_dir, 1)
            parts = parse_req_from_line(replaced_package_name, comes_from)

        yield InstallRequirement(
            parts.requirement,
            comes_from,
            link=parts.link,
            markers=parts.markers,
            extras=parts.extras,
        )


def _prepare_build_requirements(
    builder: build.ProjectBuilder,
    src_file: str,
    distributions: tuple[str, ...],
    package_name: str,
) -> Iterator[InstallRequirement]:
    result = collections.defaultdict(set)

    # Build requirements will only be present if a pyproject.toml file exists,
    # but if there is also a setup.py file then only that will be explicitly
    # processed due to the order of `DEFAULT_REQUIREMENTS_FILES`.
    src_file = os.path.join(os.path.dirname(src_file), PYPROJECT_TOML)

    for req in builder.build_system_requires:
        result[req].add(f"{package_name} ({src_file}::build-system.requires)")
    for dist in distributions:
        for req in builder.get_requires_for_build(dist):
            result[req].add(
                f"{package_name} ({src_file}::build-system.backend::{dist})"
            )

    for req, comes_from_sources in result.items():
        for comes_from in comes_from_sources:
            yield install_req_from_line(req, comes_from=comes_from)
