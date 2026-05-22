from kpi.doc.render import node_doc_markdown
from kpi.op.download.project_attribute import Latitude, Longitude


@node_doc_markdown.register
def _(_node: Latitude) -> str:
    return "Downloads the latitude of the project."


@node_doc_markdown.register
def _(_node: Longitude) -> str:
    return "Downloads the longitude of the project."
