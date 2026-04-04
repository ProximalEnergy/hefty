from kpi.workflow.transform.bess.workflow import TransformBess
from kpi.workflow.transform.pv.clean import TransformPvClean
from kpi.workflow.transform.pv.evaluate import TransformPvEvaluate
from kpi.workflow.transform.pv.summarize import TransformPvSummarize


class TransformPv(TransformPvSummarize, TransformPvEvaluate, TransformPvClean):
    pass


class Transform(TransformPv, TransformBess):
    pass
