from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from _scripts import check_pyproject_dependencies as script


def write_pyproject(*, path: Path, contents: str) -> None:
    path.write_text(dedent(contents).strip() + "\n")


def test_workspace_root_bounded_dependencies(
    *,
    tmp_path: Path,
) -> None:
    write_pyproject(
        path=tmp_path / "pyproject.toml",
        contents="""
        [project]
        name = "mono"
        version = "0.1.0"
        dependencies = [
            "polars",
            "sqlalchemy>=2,<3",
        ]

        [tool.uv.workspace]
        members = ["core"]
        """,
    )

    assert script.workspace_root_bounded_dependencies(root=tmp_path) == {
        "sqlalchemy"
    }


def test_root_pyproject_still_flags_unbounded_dependencies(
    *,
    tmp_path: Path,
) -> None:
    pyproject = tmp_path / "pyproject.toml"
    write_pyproject(
        path=pyproject,
        contents="""
        [project]
        name = "mono"
        version = "0.1.0"
        dependencies = [
            "polars",
            "sqlalchemy>=2,<3",
        ]

        [tool.uv.workspace]
        members = ["core"]
        """,
    )

    errors: list[str] = []
    script.check_pyproject(path=pyproject, errors=errors)

    assert errors == [
        f"{pyproject} [project.dependencies] "
        "has unbounded dependency: polars"
    ]


def test_subproject_only_inherits_bounded_root_dependencies(
    *,
    tmp_path: Path,
) -> None:
    write_pyproject(
        path=tmp_path / "pyproject.toml",
        contents="""
        [project]
        name = "mono"
        version = "0.1.0"
        dependencies = [
            "polars",
            "sqlalchemy>=2,<3",
        ]

        [tool.uv.workspace]
        members = ["core"]
        """,
    )
    subproject = tmp_path / "api"
    subproject.mkdir()
    pyproject = subproject / "pyproject.toml"
    write_pyproject(
        path=pyproject,
        contents="""
        [project]
        name = "api"
        version = "0.1.0"
        dependencies = [
            "polars",
            "sqlalchemy",
        ]
        """,
    )

    errors: list[str] = []
    script.check_pyproject(
        path=pyproject,
        errors=errors,
        extra_allow_unbounded=script.workspace_root_bounded_dependencies(
            root=tmp_path,
        ),
    )

    assert errors == [
        f"{pyproject} [project.dependencies] "
        "has unbounded dependency: polars"
    ]
