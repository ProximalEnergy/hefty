from kpi.base.protocol import SchemaProtocol


def inputs(schema: SchemaProtocol) -> set[str]:
    inputs = set[str]()
    for field in reversed(schema.plan.keys()):
        inputs.discard(field)
        inputs.update(schema.field_registry()[field].inputs())
    return inputs


def outputs(schema: SchemaProtocol) -> set[str]:
    outputs = set[str]()
    for field, to_delete in schema.plan.items():
        outputs = outputs.difference(to_delete)
        outputs.add(field)
    return outputs
