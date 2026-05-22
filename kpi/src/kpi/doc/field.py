from kpi.base.protocol import NodeProtocol
from kpi.doc.reference import doc_link
from kpi.doc.render import node_doc_markdown, render_doc_value
from kpi.op.field import Field


def doc_link_field[F: NodeProtocol](field: Field[F]) -> str:
    return doc_link(
        name=field.name,
        module=field._owner_module,
        qualname=f"{field._owner_qualname}.{field.name}",
    )


def doc_markdown_field[F: NodeProtocol](field: Field[F]) -> str:
    body = node_doc_markdown(field.value)
    if field.doc_header:
        return f"{field.doc_header}\n\n{body}"
    return body


@render_doc_value.register(Field)
def _[F: NodeProtocol](field: Field[F]) -> str:
    return doc_link_field(field)
