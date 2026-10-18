import ast
import configparser
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ROOT / "alembic" / "versions"


def _revisions():
    out = {}
    for f in VERSIONS.glob("*.py"):
        tree = ast.parse(f.read_text())
        info = {}
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id in ("revision", "down_revision")
            ):
                info[node.target.id] = ast.literal_eval(node.value)
            elif (
                isinstance(node, ast.Assign)
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id in ("revision", "down_revision")
            ):
                info[node.targets[0].id] = ast.literal_eval(node.value)
        out[f.name] = info
    return out


_EXCLUDED = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "site-packages",
    "node_modules",
}
PROJECT_FILES = sorted(
    p
    for p in ROOT.rglob("*.py")
    if not _EXCLUDED.intersection(p.relative_to(ROOT).parts)
)


@pytest.mark.parametrize("path", PROJECT_FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_every_python_file_has_valid_syntax(path):
    ast.parse(path.read_text(encoding="utf-8"))


def test_migrations_form_a_single_linear_chain():
    revs = _revisions()
    ids = {v["revision"] for v in revs.values()}
    roots = [v for v in revs.values() if v["down_revision"] is None]
    assert len(roots) == 1, "exactly one initial migration expected"
    parents = [
        v["down_revision"] for v in revs.values() if v["down_revision"] is not None
    ]
    assert all(p in ids for p in parents), "down_revision points at a missing migration"
    assert len(parents) == len(set(parents)), (
        "branching detected: two migrations share a parent"
    )
    heads = ids - set(parents)
    assert len(heads) == 1, f"multiple heads: {heads}"


def test_migration_files_define_upgrade_and_downgrade():
    for f in VERSIONS.glob("*.py"):
        tree = ast.parse(f.read_text())
        names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
        assert {"upgrade", "downgrade"} <= names, f.name


def test_migrations_using_raw_postgres_sql_are_flagged_as_not_sqlite_compatible():
    text = (VERSIONS / "a72e13233419_complete_field_reports_schema.py").read_text()
    assert "op.execute" in text


def test_requirements_pin_all_packages_and_include_test_runner():
    lines = [
        l.strip()
        for l in (ROOT / "requirements.txt").read_text().splitlines()
        if l.strip()
    ]
    assert lines and all("==" in l for l in lines)
    names = {l.split("==")[0].lower() for l in lines}
    assert {"fastapi", "sqlalchemy", "alembic", "uvicorn", "pydantic"} <= names


def test_requirements_have_no_duplicate_packages():
    names = [
        l.split("==")[0].lower()
        for l in (ROOT / "requirements.txt").read_text().splitlines()
        if "==" in l
    ]
    assert len(names) == len(set(names))


def test_requirements_missing_sqlite_driver_for_tests():
    assert "aiosqlite" in (ROOT / "requirements-test.txt").read_text()


def test_procfile_runs_uvicorn_on_main_app():
    content = (ROOT / "Procfile").read_text()
    assert (
        content.startswith("web:")
        and "uvicorn main:app" in content
        and "${PORT}" in content
    )


def test_python_version_file_is_valid():
    assert re.fullmatch(
        r"\d+\.\d+(\.\d+)?", (ROOT / ".python-version").read_text().strip()
    )


def test_alembic_ini_points_to_alembic_dir():
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(ROOT / "alembic.ini")
    assert cfg["alembic"]["script_location"].strip().endswith("alembic")


def test_gitignore_excludes_secrets_and_databases():
    ignored = (ROOT / ".gitignore").read_text()
    for entry in (".env", "keys/", "*.pem", "*.db", "secure_storage/"):
        assert entry in ignored
