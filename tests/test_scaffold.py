"""Smoke tests for the initial DataMind module scaffold."""

from importlib import import_module


def test_application_modules_import_with_docstrings() -> None:
    """Ensure each scaffolded application module can be imported."""
    module_names = (
        "src.llm",
        "src.snowflake_client",
        "src.config_loader",
        "src.sql_guard",
        "src.pipeline",
        "src.app",
    )

    for module_name in module_names:
        module = import_module(module_name)
        assert module.__doc__
