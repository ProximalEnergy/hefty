import aws_cdk as core
import aws_cdk.assertions as assertions

from events.events_stack import EventsStack


def test_simulation_lambda_created() -> None:
    """Run test_simulation_lambda_created."""
    app = core.App(context={"imageTag": "latest"})
    stack = EventsStack(app, "events")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties(
        "AWS::Lambda::Function",
        {"FunctionName": "pv-eem"},
    )
