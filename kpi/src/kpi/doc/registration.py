from kpi.doc import field as field_renderers
from kpi.doc import project_attribute as project_attribute_renderers
from kpi.doc import transform as transform_renderers

_REGISTERED_DOC_MODULES = (
    field_renderers,
    project_attribute_renderers,
    transform_renderers,
)


def register_doc_renderers() -> None:
    """Import documentation renderers so singledispatch registrations run."""
    _ = _REGISTERED_DOC_MODULES
