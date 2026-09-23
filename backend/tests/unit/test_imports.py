"""Verify that all core technical dependencies can be imported cleanly in the environment."""

import importlib

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "fastapi",
        "uvicorn",
        "websockets",
        "pydantic",
        "pydantic_settings",
        "numpy",
        "scipy",
        "pandas",
        "sklearn",
        "xgboost",
        "shap",
        "pyarrow",
    ],
)
def test_core_dependencies_importable(module_name: str):
    """Assert that core production dependency imports without error."""
    mod = importlib.import_module(module_name)
    assert mod is not None, f"Failed to import {module_name}"
    # Ensure package has an identifiable version string
    version = getattr(mod, "__version__", None)
    assert version is not None or module_name == "websockets"
