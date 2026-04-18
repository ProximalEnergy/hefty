from typing import TYPE_CHECKING, TypeAlias

from kpi.base.protocol import PlanProtocol, SchemaProtocol
from pydantic import RootModel


class InputDelete(RootModel[dict[str, bool]]):
    def trim(self, outputs: set[str], delete: bool = True) -> set[str]:
        inputs = self.root.keys()
        for input in inputs:
            self.root[input] = delete and (input not in outputs)
        return outputs.union(inputs)

    def drop_vars(self) -> list[str]:
        return [input for input in self.root.keys() if self.root[input]]


def delete_none(inputs: set[str]) -> InputDelete:
    return InputDelete(root={input: False for input in inputs})


class FieldPlan(RootModel[dict[str, InputDelete]]):
    def trim(self, outputs: set[str], delete: bool = True) -> set[str]:
        inputs = set[str](outputs)
        reversed_fields = list(reversed(self.root.keys()))
        for field_name in reversed_fields:
            if field_name in inputs:
                inputs.discard(field_name)
                inputs = self.root[field_name].trim(inputs, delete)
            else:
                del self.root[field_name]
        return inputs

    def outputs(self) -> set[str]:
        return set[str](self.root.keys())


# mypy gets grumpy with the recursive type but pydantic needs it
# to properly parse json-style inputs
if TYPE_CHECKING:
    PipelinePlanType = PlanProtocol
else:
    PipelinePlanType: TypeAlias = "FieldPlan | PipelinePlan"


class PipelinePlan(RootModel[dict[str, PipelinePlanType]]):
    def trim(self, outputs: set[str], delete: bool = True) -> set[str]:
        inputs = set[str](outputs)
        reversed_steps = list(reversed(self.root.keys()))
        for step_name in reversed_steps:
            outputs_created = inputs.intersection(self.root[step_name].outputs())
            if len(outputs_created) > 0:
                inputs = self.root[step_name].trim(inputs, delete)
            else:
                del self.root[step_name]
        return inputs

    def outputs(self) -> set[str]:
        return set[str]().union(*[plan.outputs() for plan in self.root.values()])


def get_plan[P: PlanProtocol](schema: SchemaProtocol[P], outputs: set[str]) -> P:
    plan = schema.full_plan()
    _ = plan.trim(outputs)
    return plan
