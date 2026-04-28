"""CDK app entry point for microservices infrastructure."""

import aws_cdk as cdk
from stacks.calendar_notifications_stack import CalendarNotificationsStack
from stacks.data_connection_outage_notifications_stack import (
    DataConnectionOutageNotificationsStack,
)
from stacks.issues_pipeline_stack import IssuesPipelineStack
from stacks.weather_alerts_stack import WeatherAlertsStack

app = cdk.App()

# Calendar Notifications Lambda Stack
CalendarNotificationsStack(
    app,
    "CalendarNotificationsLambdaStack",
    env=cdk.Environment(
        account="016997484973",
        region="us-east-2",
    ),
    description="Lambda function for calendar reminder notifications",
)

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

# Data connection outage notifications Lambda Stack
DataConnectionOutageNotificationsStack(
    app,
    "DataConnectionOutageNotificationsLambdaStack",
    env=cdk.Environment(
        account="016997484973",
        region="us-east-2",
    ),
    description="Lambda for data connection outage notifications",
)

# Automated issues pipeline Lambda Stack
IssuesPipelineStack(
    app,
    "IssuesPipelineLambdaStack",
    env=cdk.Environment(
        account="016997484973",
        region="us-east-2",
    ),
    description="Lambda function for scheduled automated issues detection",
)

app.synth()
