"""Built-in tests for device and tag validation."""

from typing import TYPE_CHECKING, Any

from core.enumerations import DeviceType

from inspectui.core.models import TestResult
from inspectui.core.tests.base import BaseTest, TestParameter, TestRegistry

if TYPE_CHECKING:
    from inspectui.core.cache import CacheManager


@TestRegistry.register
class SensorTypeUniquePerDeviceTest(BaseTest):
    """Check sensor type appears at most once per device."""

    name = "sensor_type_unique_per_device"
    description = "Verify each device has at most one tag for sensor type"
    category = "relationships"

    parameters = [
        TestParameter(
            name="sensor_type_ids",
            param_type="int_list",
            description="Sensor type IDs that must not duplicate on a device",
            default=[],
            required=True,
        ),
    ]

    def run_test(self, cache: "CacheManager") -> TestResult:
        """Run duplicate sensor-type check per device."""
        sensor_type_ids = self.get_param("sensor_type_ids") or []
        if not sensor_type_ids:
            return self.skip("At least one sensor type ID is required")

        total_devices_with_sensor_type = 0
        duplicate_entries: list[dict[str, int]] = []

        for sensor_type_id in sensor_type_ids:
            counts_by_device: dict[int, int] = {}
            for tag in cache.tags:
                if tag.sensor_type_id != sensor_type_id:
                    continue
                counts_by_device[tag.device_id] = (
                    counts_by_device.get(tag.device_id, 0) + 1
                )

            total_devices_with_sensor_type += len(counts_by_device)
            for device_id, count in counts_by_device.items():
                if count > 1:
                    duplicate_entries.append(
                        {
                            "sensor_type_id": sensor_type_id,
                            "device_id": device_id,
                            "count": count,
                        }
                    )

        passed = len(duplicate_entries) == 0
        sensor_type_label = ", ".join(str(x) for x in sensor_type_ids)

        if passed:
            message = (
                "No duplicate tags found for sensor types "
                f"{sensor_type_label} across {total_devices_with_sensor_type} "
                "device matches"
            )
        else:
            message = (
                f"Found {len(duplicate_entries)} duplicate device/sensor pairs for "
                f"sensor types {sensor_type_label}"
            )

        per_type_dup: dict[int, list[dict[str, int]]] = {
            stid: [] for stid in sensor_type_ids
        }
        for entry in duplicate_entries:
            sid = int(entry["sensor_type_id"])
            if sid in per_type_dup:
                per_type_dup[sid].append(entry)

        conditions: list[dict[str, object]] = []
        for stid in sorted(sensor_type_ids):
            dups = per_type_dup.get(stid, [])
            cond_passed = len(dups) == 0
            if cond_passed:
                detail = "no duplicate device/tag pairs for this type"
            else:
                detail = f"{len(dups)} duplicate device/tag pair(s)"
            conditions.append(
                {
                    "label": f"sensor type {stid}",
                    "passed": cond_passed,
                    "detail": detail,
                },
            )

        return TestResult(
            test_name=self.name,
            passed=passed,
            message=message,
            details={
                "sensor_type_ids": sensor_type_ids,
                "device_matches": total_devices_with_sensor_type,
                "duplicates": duplicate_entries[:10],
                "conditions": conditions,
            },
        )


@TestRegistry.register
class ParentDeviceTypeAllowlistTest(BaseTest):
    """Check that selected child types have parent in an allowlist."""

    name = "parent_device_type_allowlist"
    description = "Verify child device types have allowed parent device types"
    category = "relationships"

    parameters = [
        TestParameter(
            name="child_parent_type_rules",
            param_type="str",
            description=(
                "Rules map of child type -> allowed parent types. Example: 1:2,3;2:7"
            ),
            default={},
            required=True,
        ),
    ]

    def run_test(self, cache: "CacheManager") -> TestResult:
        """Run parent device type allowlist validation."""
        raw_rules = self.get_param("child_parent_type_rules")
        try:
            rules = self._parse_rules(raw_rules)
        except ValueError as exc:
            return self.error(f"Invalid child_parent_type_rules: {exc}")

        if not rules:
            return self.skip("At least one child->parent rule is required")

        invalid_devices: list[dict[str, int | str]] = []
        per_rule: dict[int, dict[str, int]] = {
            cid: {"checked": 0, "invalid": 0} for cid in rules
        }

        for device in cache.devices:
            allowed_parent_types = rules.get(device.device_type_id)
            if allowed_parent_types is None:
                continue

            cid = device.device_type_id
            per_rule[cid]["checked"] += 1
            if device.parent_device_id is None:
                per_rule[cid]["invalid"] += 1
                invalid_devices.append(
                    {
                        "device_id": device.device_id,
                        "child_type_id": device.device_type_id,
                        "issue": "no parent",
                    }
                )
                continue

            parent = cache.get_device(device.parent_device_id)
            if parent is None:
                per_rule[cid]["invalid"] += 1
                invalid_devices.append(
                    {
                        "device_id": device.device_id,
                        "child_type_id": device.device_type_id,
                        "parent_device_id": device.parent_device_id,
                        "issue": "parent not found",
                    }
                )
                continue

            if parent.device_type_id not in allowed_parent_types:
                per_rule[cid]["invalid"] += 1
                invalid_devices.append(
                    {
                        "device_id": device.device_id,
                        "child_type_id": device.device_type_id,
                        "parent_device_id": parent.device_id,
                        "parent_type_id": parent.device_type_id,
                        "issue": "parent type not allowed",
                    }
                )

        checked_count = sum(s["checked"] for s in per_rule.values())
        conditions: list[dict[str, object]] = []
        for cid in sorted(rules.keys()):
            allowed = rules[cid]
            stats = per_rule[cid]
            chk = stats["checked"]
            inv = stats["invalid"]
            parents_label = ",".join(str(x) for x in sorted(allowed))
            label = f"child type {cid} → parent types [{parents_label}]"
            cond_passed = inv == 0
            if chk == 0:
                detail = "no devices with this child type"
            elif cond_passed:
                detail = f"{chk} device(s), all valid"
            else:
                detail = f"{chk} checked, {inv} invalid"
            conditions.append(
                {
                    "label": label,
                    "passed": cond_passed,
                    "detail": detail,
                },
            )

        passed = len(invalid_devices) == 0
        if passed:
            message = (
                f"All {checked_count} checked devices have allowed parent device types"
            )
        else:
            message = (
                f"{len(invalid_devices)}/{checked_count} checked devices have "
                "invalid parents"
            )

        rules_for_storage = {cid: sorted(allowed) for cid, allowed in rules.items()}

        return TestResult(
            test_name=self.name,
            passed=passed,
            message=message,
            details={
                "child_parent_type_rules": rules_for_storage,
                "checked_devices": checked_count,
                "invalid_devices": invalid_devices[:10],
                "conditions": conditions,
            },
        )

    @staticmethod
    def _parse_rules(raw_rules: object) -> dict[int, set[int]]:
        """Parse child->allowed-parent rules from dict or string."""
        if raw_rules is None or raw_rules == "":
            return {}

        if isinstance(raw_rules, dict):
            parsed: dict[int, set[int]] = {}
            for child_raw, allowed_raw in raw_rules.items():
                child_type_id = int(child_raw)
                if isinstance(allowed_raw, list):
                    parsed[child_type_id] = {int(x) for x in allowed_raw}
                else:
                    parsed[child_type_id] = {int(allowed_raw)}
            return parsed

        if isinstance(raw_rules, str):
            parsed: dict[int, set[int]] = {}
            segments = raw_rules.replace("\n", ";").split(";")
            for segment in segments:
                cleaned = segment.strip()
                if not cleaned:
                    continue
                if ":" not in cleaned:
                    raise ValueError(
                        f"Missing ':' in segment '{cleaned}'. "
                        "Use format 'child:parent1,parent2'"
                    )
                child_raw, parents_raw = cleaned.split(":", maxsplit=1)
                child_type_id = int(child_raw.strip())
                parent_parts = parents_raw.replace(",", " ").split()
                if not parent_parts:
                    raise ValueError(
                        f"No parent types provided for child type {child_type_id}"
                    )
                parsed[child_type_id] = {int(x) for x in parent_parts}
            return parsed

        raise ValueError("Expected dict or string")


def _coerce_device_type_ids(raw: object) -> list[int]:
    """Normalize param value to ``device_type_id`` ints (enum members allowed)."""
    if raw is None:
        return []
    if not isinstance(raw, list):
        return []
    out: list[int] = []
    for x in raw:
        out.append(int(x))
    return out


def _device_type_label(*, type_id: int) -> str:
    """Human-readable device type name when ``DeviceType`` has the value."""
    try:
        return f"{DeviceType(type_id).name} ({type_id})"
    except ValueError:
        return f"device_type_id={type_id}"


@TestRegistry.register
class RequiredDeviceModelsTest(BaseTest):
    """Require ``device_model_id`` for devices of given device types."""

    name = "required_device_models"
    description = (
        "Verify devices of selected types have device_model_id set "
        "(FK to operational.device_models)"
    )
    category = "relationships"

    parameters = [
        TestParameter(
            name="device_type_ids",
            param_type="int_list",
            description=(
                "Device types (IDs / DeviceType enum values) that must have "
                "device_model_id on every device"
            ),
            default=[],
            required=True,
        ),
    ]

    def run_test(self, cache: "CacheManager") -> TestResult:
        """Require ``device_model_id`` for configured device types."""
        type_ids = _coerce_device_type_ids(self.get_param("device_type_ids"))
        if not type_ids:
            return self.skip("At least one device_type_id is required")

        required = frozenset(type_ids)
        missing: list[dict[str, Any]] = []
        for d in cache.devices:
            if d.device_type_id not in required:
                continue
            if d.device_model_id is not None:
                continue
            missing.append(
                {
                    "device_id": d.device_id,
                    "device_type_id": d.device_type_id,
                    "device_type_label": _device_type_label(
                        type_id=d.device_type_id,
                    ),
                    "name_short": d.name_short,
                    "name_long": d.name_long,
                },
            )

        passed = len(missing) == 0
        by_type: dict[int, list[dict[str, Any]]] = {tid: [] for tid in required}
        for m in missing:
            tid = int(m["device_type_id"])
            if tid in by_type:
                by_type[tid].append(m)

        conditions: list[dict[str, object]] = []
        for tid in sorted(required):
            bad = by_type.get(tid, [])
            cond_passed = len(bad) == 0
            label = _device_type_label(type_id=tid)
            if cond_passed:
                detail = "all devices have device_model_id"
            else:
                detail = f"{len(bad)} device(s) missing device_model_id"
            conditions.append(
                {
                    "label": label,
                    "passed": cond_passed,
                    "detail": detail,
                },
            )

        if passed:
            n_checked = sum(1 for d in cache.devices if d.device_type_id in required)
            message = (
                f"All {n_checked} devices of the selected types have "
                "device_model_id set"
            )
        else:
            message = (
                f"{len(missing)} device(s) of {len(required)} type(s) lack "
                "device_model_id"
            )

        return TestResult(
            test_name=self.name,
            passed=passed,
            message=message,
            details={
                "device_type_ids": sorted(required),
                "devices_missing_model": missing[:50],
                "conditions": conditions,
            },
        )
