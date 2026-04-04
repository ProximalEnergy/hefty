from kpi.workflow.transform.bess.summarize.availability import (
    TransformBessSummarizeAvailability,
)
from kpi.workflow.transform.bess.summarize.energy import TransformBessSummarizeEnergy
from kpi.workflow.transform.bess.summarize.other import TransformBessSummarizeOther
from kpi.workflow.transform.bess.summarize.power import TransformBessSummarizePower
from kpi.workflow.transform.bess.summarize.soc import TransformBessSummarizeSoc


class TransformBessSummarize(
    TransformBessSummarizeSoc,
    TransformBessSummarizePower,
    TransformBessSummarizeOther,
    TransformBessSummarizeEnergy,
    TransformBessSummarizeAvailability,
):
    pass
