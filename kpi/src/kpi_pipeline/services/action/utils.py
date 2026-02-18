from kpi_pipeline.base.protocols import ActionProtocol


def is_empty(transform: ActionProtocol) -> bool:
    return transform.nominal_outputs() == []


def is_identity(transform: ActionProtocol) -> bool:
    return transform.pass_through and is_empty(transform)


def through_outputs(
    transform: ActionProtocol, previous_outputs: list[str] = []
) -> list[str]:
    if transform.pass_through:
        return list(set(previous_outputs) | set(transform.nominal_outputs()))
    else:
        return transform.nominal_outputs()
