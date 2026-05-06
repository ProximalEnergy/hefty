from typing import Any

from cmms_ticket_download.dbquery import (
    execute_bulk_upsert_cmms_tickets,
)


def bulk_upsert_cmms_tickets(*, schema: str, tickets_data: list[dict[str, Any]]) -> int:
    """Upsert multiple CMMS tickets efficiently.

    Args:
        schema: Project schema to write into.
        tickets_data: CMMS ticket rows to insert or update.
    """

    return execute_bulk_upsert_cmms_tickets(
        schema=schema,
        tickets_data=tickets_data,
    )


if __name__ == "__main__":
    import datetime

    tickets_data = [
        {
            "cmms_integration_id": 3,
            "source_id": 1001,
            "key": "TICKET-2024-001",
            "source_created_at": datetime.datetime(2024, 1, 15, 10, 30, 0),
            "due_date": datetime.datetime(2024, 1, 22, 17, 0, 0),
            "summary": "Temperature sensor malfunction on Unit 5",
            "summary_long": (
                "The temperature sensor on Unit 5 in Building A is reporting values "
                "that are consistently 10 degrees higher than expected. This is "
                "affecting the HVAC system performance."
            ),
            "status": "Open",
            "status_change_at": datetime.datetime(2024, 1, 15, 10, 30, 0),
            "priority": "High",
            "reporter": "john.doe@company.com",
            "assigned_to": "jane.smith@company.com",
            "location": "Building A, Floor 2, Unit 5",
            "cmms_device_id": "TEMP-SENSOR-005",
            "cmms_device_name": "Temperature Sensor Unit 5",
            "link": "https://cmms.company.com/tickets/1001",
            "json_raw": {
                "custom_fields": {
                    "department": "Facilities",
                    "equipment_type": "HVAC",
                    "urgency_score": 8,
                },
                "metadata": {"source": "api", "imported_at": "2024-01-15T10:30:00Z"},
            },
        },
        {
            "cmms_integration_id": 4,
            "source_id": 1003,
            "key": "TICKET-2024-002",
            "source_created_at": datetime.datetime(2024, 1, 16, 14, 15, 0),
            "due_date": datetime.datetime(2024, 1, 30, 17, 0, 0),
            "summary": "Preventive maintenance for Generator 3",
            "summary_long": (
                "Scheduled preventive maintenance for backup generator 3. Includes "
                "oil change, filter replacement, and load testing."
            ),
            "status": "In Progress",
            "status_change_at": datetime.datetime(2024, 1, 16, 14, 15, 0),
            "priority": "Medium",
            "reporter": "maintenance@company.com",
            "assigned_to": "mike.wilson@company.com",
            "location": "Generator Room, Basement",
            "cmms_device_id": "GEN-003",
            "cmms_device_name": "Backup Generator 3",
            "link": "https://cmms.company.com/tickets/1002",
            "json_raw": {
                "custom_fields": {
                    "department": "Maintenance",
                    "equipment_type": "Generator",
                    "maintenance_type": "Preventive",
                },
                "metadata": {
                    "source": "scheduled",
                    "recurring": True,
                    "frequency": "monthly",
                },
            },
        },
        {
            "cmms_integration_id": 4,
            "source_id": 2002,
            "key": "TICKET-2024-003",
            "source_created_at": datetime.datetime(2024, 1, 17, 9, 45, 0),
            "due_date": datetime.datetime(2024, 1, 24, 12, 0, 0),
            "summary": "Emergency: Water leak in server room",
            "summary_long": (
                "Water leak detected in server room ceiling. Immediate attention "
                "required to prevent equipment damage."
            ),
            "status": "Urgent",
            "status_change_at": datetime.datetime(2024, 1, 17, 9, 45, 0),
            "priority": "Critical",
            "reporter": "security@company.com",
            "assigned_to": "emergency@company.com",
            "location": "Server Room, Floor 1",
            "cmms_device_id": "SERVER-RM-001",
            "cmms_device_name": "Server Room Environmental Monitor",
            "link": "https://cmms.company.com/tickets/2001",
            "json_raw": {
                "custom_fields": {
                    "department": "IT",
                    "equipment_type": "Infrastructure",
                    "emergency_level": "Critical",
                    "affected_systems": ["servers", "networking", "cooling"],
                },
                "metadata": {
                    "source": "automated_alert",
                    "alert_type": "water_detection",
                    "escalated": True,
                },
            },
        },
    ]

    def run_cmms_ticket_crud_debug():
        """Run a local bulk upsert smoke test with sample ticket data."""

        bulk_upsert_cmms_tickets(
            schema="continental_v2",
            tickets_data=tickets_data,
        )

    run_cmms_ticket_crud_debug()
