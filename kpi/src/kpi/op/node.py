from abc import ABC

from pydantic import BaseModel


class NodeModel(BaseModel, ABC):
    def inputs(self) -> set[str]:
        return set()


def node_type[P: NodeModel](cls: type[P]) -> type[P]:
    return cls
