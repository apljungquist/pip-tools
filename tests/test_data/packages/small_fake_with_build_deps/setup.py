from __future__ import annotations

from setuptools import setup

setup(
    name="small_fake_with_build_deps",
    version=0.1,
    install_requires=[
        "small_fake_d",
    ],
    extras_require={
        "e": ["small_fake_e"],
    },
)
