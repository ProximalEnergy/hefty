"""CDK app entry point for microservices infrastructure."""

import aws_cdk as cdk
from stacks.weather_alerts_stack import WeatherAlertsStack

app = cdk.App()

# Weather Alerts Lambda Stack
WeatherAlertsStack(
    app,
    "WeatherAlertsLambdaStack",
    env=cdk.Environment(
        account="016997484973",
        region="us-east-2",
    ),
    description="Lambda function for NWS weather alert notifications",
)

app.synth()
