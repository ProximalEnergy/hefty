from kpi.registry.transform.bess.clean.api import TransformBessClean
from kpi.registry.transform.bess.evaluate.api import TransformBessEvaluate
from kpi.registry.transform.bess.summarize.api import TransformBessSummarize


class TransformBess(TransformBessSummarize, TransformBessEvaluate, TransformBessClean):
    pass
