from typing import Self

from kpi.base.protocol import PlanProtocol, SchemaProtocol, plan_protocol
from pydantic import BaseModel, model_validator


class SingleFieldPlan(BaseModel):
    field_name: str
    inputs: dict[str, bool]

    @model_validator(mode="after")
    def field_name_not_in_inputs(self) -> Self:
        if self.field_name in self.inputs:
            raise ValueError(
                "field_name must not be a key in inputs (no self-dependency)"
            )
        return self

    def trim(self, outputs: set[str], delete: bool = True) -> set[str]:
        inputs = outputs - {self.field_name}
        for input in self.inputs.keys():
            self.inputs[input] = delete and (input not in inputs)
            inputs.add(input)
        return inputs

    def to_delete(self) -> set[str]:
        return {input for input in self.inputs.keys() if self.inputs[input]}


@plan_protocol
class MultiFieldPlan(BaseModel):
    fields: list[SingleFieldPlan]

    def trim(self, outputs: set[str], delete: bool = True) -> set[str]:
        inputs = set[str](outputs)
        reversed_plan: list[SingleFieldPlan] = []
        for single_field_plan in reversed(self.fields):
            if single_field_plan.field_name in inputs:
                inputs = single_field_plan.trim(inputs, delete)
                reversed_plan.append(single_field_plan)

        self.fields = list(reversed(reversed_plan))
        return inputs

    @model_validator(mode="after")
    def no_duplicate_field_names(self) -> Self:
        outputs = self.outputs()
        if len(outputs) != len(set(outputs)):
            raise ValueError("duplicate field names in MultiFieldPlan")
        return self

    def outputs(self) -> list[str]:
        return [field.field_name for field in self.fields]


@plan_protocol
class PipelinePlan(BaseModel):
    steps: dict[str, Self | MultiFieldPlan]

    def trim(self, outputs: set[str], delete: bool = True) -> set[str]:
        inputs = set[str](outputs)
        reversed_plan: dict[str, Self | MultiFieldPlan] = {}
        for step_name, sub_plan in reversed(self.steps.items()):
            outputs_created = inputs.intersection(sub_plan.outputs())
            if outputs_created:
                inputs = sub_plan.trim(inputs, delete)
                reversed_plan[step_name] = sub_plan
        self.steps = {
            step_name: plan for step_name, plan in reversed(reversed_plan.items())
        }
        return inputs

    def outputs(self) -> list[str]:
        outputs: list[str] = []
        for step_plan in self.steps.values():
            outputs.extend(step_plan.outputs())
        return outputs

    @model_validator(mode="after")
    def no_duplicate_field_names(self) -> Self:
        outputs = self.outputs()
        if len(outputs) != len(set(outputs)):
            raise ValueError("duplicate field names in PipelinePlan")
        return self


def get_plan[P: PlanProtocol](
    *, schema: SchemaProtocol[P], outputs: set[str], delete: bool = True
) -> P:
    plan = schema.full_plan()
    _ = plan.trim(outputs, delete=delete)
    return plan
