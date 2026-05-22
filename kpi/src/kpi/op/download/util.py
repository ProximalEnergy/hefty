from kpi.base.protocol import node_protocol
from pydantic import BaseModel


@node_protocol
class MarkdownDocModel(BaseModel):
    def inputs(self) -> set[str]:
        return set[str]()
