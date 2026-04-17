from kpi.registry.transform.bess.api import TransformBess
from kpi.registry.transform.pv.clean import TransformPvClean
from kpi.registry.transform.pv.evaluate import TransformPvEvaluate
from kpi.registry.transform.pv.summarize import TransformPvSummarize


class TransformPv(TransformPvSummarize, TransformPvEvaluate, TransformPvClean):
    pass


class Transform(TransformPv, TransformBess):
    pass
