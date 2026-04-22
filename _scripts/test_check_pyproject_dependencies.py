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


def test_workspace_root_bounded_dependencies_without_workspace(
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
            "sqlalchemy>=2,<3",
        ]
        """,
    )

    assert script.workspace_root_bounded_dependencies(root=tmp_path) == set()


def test_workspace_root_bounded_dependencies_respect_sources(
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
            "core",
            "sqlalchemy>=2,<3",
        ]

        [tool.uv.workspace]
        members = ["core"]

        [tool.uv.sources]
        core = { workspace = true }
        """,
    )

    assert script.workspace_root_bounded_dependencies(root=tmp_path) == {
        "core",
        "sqlalchemy",
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


def test_subproject_dev_group_inherits_root_dev_group_dependencies(
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
            "sqlalchemy>=2,<3",
        ]

        [dependency-groups]
        dev = [
            "pandas-stubs~=3.0",
        ]

        [tool.uv.workspace]
        members = ["api"]
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
            "sqlalchemy",
        ]

        [dependency-groups]
        dev = [
            "pandas-stubs",
        ]
        """,
    )

    root_bounded, root_group_bounded = script.workspace_root_dependencies(
        root=tmp_path,
    )
    errors: list[str] = []
    script.check_pyproject(
        path=pyproject,
        errors=errors,
        extra_allow_unbounded=root_bounded,
        extra_group_allow_unbounded=root_group_bounded,
    )

    assert errors == []


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
