"""Architecture boundary tests asserting Clean Architecture layer isolation."""

import ast
from pathlib import Path


def get_domain_python_files() -> list[Path]:
    """Recursively collect all Python files in the domain layer."""
    domain_dir = Path(__file__).resolve().parent.parent.parent / "app" / "domain"
    assert domain_dir.exists(), f"Domain directory {domain_dir} does not exist"
    return list(domain_dir.rglob("*.py"))


def test_domain_layer_has_zero_framework_dependencies():
    """Assert that the Domain Layer has NO imports from web, database, or infrastructure frameworks."""
    forbidden_modules = {
        "fastapi",
        "starlette",
        "uvicorn",
        "websockets",
        "sqlite3",
        "sqlalchemy",
        "duckdb",
        "pyarrow",
        "requests",
        "httpx",
        "aiohttp",
        "socket",
        "app.api",
        "app.application",
        "app.infrastructure",
    }

    violations = []
    domain_files = get_domain_python_files()
    assert len(domain_files) > 0, "No domain files found to inspect"

    for py_file in domain_files:
        with open(py_file, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(py_file))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_modules:
                        if alias.name == forbidden or alias.name.startswith(f"{forbidden}."):
                            violations.append(
                                f"{py_file.name}:{node.lineno} imports '{alias.name}'"
                            )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for forbidden in forbidden_modules:
                        if node.module == forbidden or node.module.startswith(f"{forbidden}."):
                            violations.append(
                                f"{py_file.name}:{node.lineno} imports from '{node.module}'"
                            )

    assert not violations, (
        "Architectural Boundary Violations detected in Domain Layer:\n" + "\n".join(violations)
    )
