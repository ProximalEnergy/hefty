import datetime
from core.enumerations import ProjectID
from dotenv import load_dotenv
from kpi.op.create import create_dataset
from kpi.op.observer import LocalObserver, set_global_observer
from kpi.op.plan import get_plan
from kpi.op.util import tidy
from kpi.schema.api import get_pipeline
from kpi.registry.transform.bess.evaluate.api import TransformBessEvaluate as Eval

NER_INPUTS = {
    Eval.physical_total_usd_h.name,
    Eval.virtual_net_usd_h.name,
    Eval.project_ner_availability_h.name,
}

project_id = ProjectID.GREGORY_INDIE.value
start_date = datetime.date(2026, 4, 24)
end_date = datetime.date(2026, 4, 26)

load_dotenv()


set_global_observer(LocalObserver())


Pipeline = get_pipeline(project_id=project_id)
pipeline = Pipeline()

plan = get_plan(
    schema=pipeline,
    outputs=NER_INPUTS,
)

dataset = create_dataset(
    project_id=project_id,
    start_date=start_date,
    end_date=end_date,
)
dataset = pipeline.download.run(
    dataset=dataset, plan=plan.steps[Pipeline.download.name]
)


ds = tidy(
    pipeline.transform.run(dataset=dataset, plan=plan.steps[Pipeline.transform.name])
)
print(ds)


ds.to_pandas().to_csv("_data/ner_report.csv")
