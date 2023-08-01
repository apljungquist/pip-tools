from __future__ import annotations

import setuptools.build_meta

# Re-export all names in case more hooks are added in the future
from setuptools.build_meta import *  # noqa: F401, F403

# FIXME: install static build deps somehow
# Here the backend imports another dep but the same problem applies if the backend
# itself is not installed in the environment where pip-compile runs.
# import fake_static_build_dep

build_wheel = setuptools.build_meta.build_wheel
build_sdist = setuptools.build_meta.build_sdist


def get_requires_for_build_sdist(config_settings=None):
    result = setuptools.build_meta.get_requires_for_build_sdist(config_settings)
    assert result == []
    result.append("fake_dynamic_build_dep_for_all")
    result.append("fake_dynamic_build_dep_for_sdist")
    return result


def get_requires_for_build_wheel(config_settings=None):
    result = setuptools.build_meta.get_requires_for_build_wheel(config_settings)
    assert result == ["wheel"]
    result.append("fake_dynamic_build_dep_for_all")
    result.append("fake_dynamic_build_dep_for_wheel")
    return result


def get_requires_for_build_editable(config_settings=None):
    return ["fake_dynamic_build_dep_for_all", "fake_dynamic_build_dep_for_editable"]
