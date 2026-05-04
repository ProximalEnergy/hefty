from kpi.registry.transform.bess.evaluate.kpi import TransformBessEvaluateKpi
from kpi.registry.transform.bess.evaluate.tenaska import TransformBessEvaluateTenaska


class TransformBessEvaluate(
    TransformBessEvaluateTenaska,
    TransformBessEvaluateKpi,
):
    pass
