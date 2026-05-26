from pydantic import BaseModel


class NoInputsModel(BaseModel):
    def inputs(self) -> set[str]:
        return set[str]()
