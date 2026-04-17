from kpi.registry.transform.bess.summarize.availability import (
    TransformBessSummarizeAvailability,
)
from kpi.registry.transform.bess.summarize.energy import TransformBessSummarizeEnergy
from kpi.registry.transform.bess.summarize.other import TransformBessSummarizeOther
from kpi.registry.transform.bess.summarize.power import TransformBessSummarizePower
from kpi.registry.transform.bess.summarize.soc import TransformBessSummarizeSoc


class TransformBessSummarize(
    TransformBessSummarizeSoc,
    TransformBessSummarizePower,
    TransformBessSummarizeOther,
    TransformBessSummarizeEnergy,
    TransformBessSummarizeAvailability,
):
    pass
