from kpi.base.protocol import NodeProtocol
from kpi.doc.reference import doc_link_field_ref
from kpi.doc.render import node_doc_markdown, render_doc_value
from kpi.op.field import Field, FieldRef


def doc_markdown_field[F: NodeProtocol](field: Field[F]) -> str:
    body = node_doc_markdown(field.value)
    if field.doc_header:
        return f"{field.doc_header}\n\n{body}"
    return body


@render_doc_value.register(FieldRef)
def _(obj: FieldRef) -> str:
    return doc_link_field_ref(obj)
