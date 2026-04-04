from kpi.workflow.transform.bess.clean.workflow import TransformBessClean
from kpi.workflow.transform.bess.evaluate.evaluate import TransformBessEvaluate
from kpi.workflow.transform.bess.summarize.workflow import TransformBessSummarize


class TransformBess(TransformBessSummarize, TransformBessEvaluate, TransformBessClean):
    pass
