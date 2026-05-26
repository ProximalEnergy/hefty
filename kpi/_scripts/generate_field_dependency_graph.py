from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from kpi.op.field import Field, FieldRef
from kpi.registry.download.api import DownloadRegistry
from kpi.registry.api import FULL_REGISTRY
from kpi.registry.transform.api import Transform
from kpi.registry.upload.api import UPLOAD

OUTPUT_PATH = Path("docs/generated/field_dependency_graph.js")
EXCLUDED_FIELDS = {"date_local_5m"}


def _doc_path_from_module(*, module_name: str) -> str:
    registry_module = module_name.removeprefix("kpi.registry.")
    return f"/{registry_module.replace('.', '/')}/"


def _doc_anchor(field_ref: FieldRef) -> str:
    return f"{field_ref.module}.{field_ref.qualname}.{field_ref.name}"


def _node_element(
    *,
    field_name: str,
    phase: str,
    doc_path: str | None,
    doc_anchor: str | None,
    can_link_to_docs: bool,
) -> dict[str, dict[str, str | bool]]:
    data: dict[str, str | bool] = {
        "id": field_name,
        "label": field_name,
        "phase": phase,
        "canLinkToDocs": can_link_to_docs,
    }
    if doc_path is not None:
        data["docPath"] = doc_path
    if doc_anchor is not None:
        data["docAnchor"] = doc_anchor
    return {"data": data}


def _edge_element(
    *, source_name: str, target_name: str
) -> dict[str, dict[str, str | bool]]:
    edge_id = f"{source_name}__to__{target_name}"
    return {
        "data": {
            "id": edge_id,
            "source": source_name,
            "target": target_name,
        }
    }


def build_elements() -> dict[str, list[dict[str, dict[str, str | bool]]]]:
    download_fields = {
        field_name
        for field_name in DownloadRegistry.map().keys()
        if field_name not in EXCLUDED_FIELDS
    }
    upload_fields = {
        field_name for field_name in UPLOAD.keys() if field_name not in EXCLUDED_FIELDS
    }
    docs_metadata: dict[str, tuple[str, str]] = {}
    for field_name, field in cast(
        dict[str, Field[Any]],
        {
            **DownloadRegistry.field_map(),
            **Transform.field_map(),
        },
    ).items():
        if field_name in EXCLUDED_FIELDS:
            continue
        docs_metadata[field_name] = (
            _doc_path_from_module(module_name=field.ref.module),
            _doc_anchor(field.ref),
        )
    known_fields = {
        field_name
        for field_name in FULL_REGISTRY.keys()
        if field_name not in EXCLUDED_FIELDS
    }
    edges: list[tuple[str, str]] = []

    for field_name, node in FULL_REGISTRY.items():
        if field_name in EXCLUDED_FIELDS:
            continue
        for input_name in sorted(node.inputs()):
            if input_name in EXCLUDED_FIELDS:
                continue
            edges.append((input_name, field_name))
            known_fields.add(input_name)

    sorted_fields = sorted(known_fields)
    node_elements: list[dict[str, dict[str, str | bool]]] = []
    for name in sorted_fields:
        if name in upload_fields:
            phase = "kpi"
        elif name in download_fields:
            phase = "download"
        elif name in FULL_REGISTRY:
            phase = "transform"
        else:
            phase = "external"
        doc_path, doc_anchor = docs_metadata.get(name, (None, None))
        can_link_to_docs = (
            phase != "kpi" and doc_path is not None and doc_anchor is not None
        )
        node_elements.append(
            _node_element(
                field_name=name,
                phase=phase,
                doc_path=doc_path,
                doc_anchor=doc_anchor,
                can_link_to_docs=can_link_to_docs,
            )
        )
    edge_elements = [
        _edge_element(source_name=source, target_name=target)
        for source, target in sorted(set(edges))
    ]
    return {"nodes": node_elements, "edges": edge_elements}


def generate_field_dependency_graph_main() -> None:
    payload = build_elements()
    output_text = (
        "window.FIELD_DEP_GRAPH = "
        f"{json.dumps(payload, indent=2, sort_keys=True)};\n"
    )
    OUTPUT_PATH.write_text(output_text, encoding="utf-8")


if __name__ == "__main__":
    generate_field_dependency_graph_main()
