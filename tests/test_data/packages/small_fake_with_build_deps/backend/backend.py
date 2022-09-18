from __future__ import annotations

import setuptools.build_meta

# Re-export all names in case more hooks are added in the future
from setuptools.build_meta import *  # noqa: F401, F403

build_wheel = setuptools.build_meta.build_wheel
build_sdist = setuptools.build_meta.build_sdist


def get_requires_for_build_sdist(config_settings=None):
    result = setuptools.build_meta.get_requires_for_build_sdist(config_settings)
    assert result == []
    result.append("small-fake-a")
    return result


def get_requires_for_build_wheel(config_settings=None):
    result = setuptools.build_meta.get_requires_for_build_wheel(config_settings)
    assert result == ["wheel"]
    result.append("small-fake-b")
    return result


def get_requires_for_build_editable(config_settings=None):
    return ["small-fake-c"]
