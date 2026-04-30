"""Utilities for looking up PTP acronym information from CSV data.

This module provides functions to query acronym metadata including
human-readable descriptions, granularity, sequences, and endpoints.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AcronymInfo:
    """Information about a PTP acronym."""

    keyname: str
    element_definition: str
    granularity_minutes: int
    sequence: str
    dimensions: str
    description: str
    endpoint: str
    unit: str | None = None
    ui_group: str | None = None
    ui_subgroup: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> AcronymInfo:
        """Create AcronymInfo from dictionary."""
        granularity_str = data["Granularity (Minutes)"].strip()
        try:
            granularity_minutes = int(granularity_str)
        except ValueError:
            # Handle non-numeric values like "Meta"
            granularity_minutes = 0
        return cls(
            keyname=data["Keyname"],
            element_definition=data["Element Definition"],
            granularity_minutes=granularity_minutes,
            sequence=data["Sequence"],
            dimensions=data["Dimension(s)"],
            description=data["Description"],
            endpoint=data["Endpoint"],
            unit=data.get("Unit", "").strip() or None,
            ui_group=data.get("UI_Group", "").strip() or None,
            ui_subgroup=data.get("UI_Subgroup", "").strip() or None,
        )


class AcronymLookup:
    """Lookup utility for PTP acronyms.

    Note: Some acronyms appear multiple times with different granularities
    and endpoints. Use get_all_by_keyname() to get all matches, or get()
    with endpoint parameter to get a specific match.
    """

    def __init__(self, csv_path: Path | None = None):
        """Initialize the lookup with CSV data.

        Args:
            csv_path: Path to the PTP_acronyms CSV file. If None, uses
                the categorized CSV file (tenaska_acronyms_categorized.csv).
        """
        if csv_path is None:
            csv_path = (
                Path(__file__).parent
                / "endpoint_docs"
                / "tenaska_acronyms_categorized.csv"
            )
        # Store all acronyms (some appear multiple times)
        self._acronyms: dict[str, list[AcronymInfo]] = {}
        self._load_csv(csv_path)

    def _load_csv(self, csv_path: Path) -> None:
        """Load acronym data from CSV file."""
        with csv_path.open(encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip empty rows
                keyname = row.get("Keyname", "").strip()
                if not keyname:
                    continue
                # Skip metadata rows (those with "Meta" granularity)
                granularity_str = row.get("Granularity (Minutes)", "").strip()
                if granularity_str == "Meta":
                    continue
                acronym = AcronymInfo.from_dict(row)
                # Store all occurrences (some acronyms appear multiple times)
                if keyname not in self._acronyms:
                    self._acronyms[keyname] = []
                self._acronyms[keyname].append(acronym)

    def get(self, keyname: str, endpoint: str | None = None) -> AcronymInfo | None:
        """Get information for a specific acronym.

        Args:
            keyname: The acronym keyname (e.g., "BLTRAMT").
            endpoint: Optional endpoint name to filter by. If provided,
                returns the first match for this endpoint. If None and
                multiple matches exist, returns the first one.

        Returns:
            AcronymInfo if found, None otherwise.
        """
        matches = self._acronyms.get(keyname.upper())
        if not matches:
            return None
        if endpoint:
            for match in matches:
                if match.endpoint == endpoint:
                    return match
        # Return first match if no endpoint specified
        return matches[0]

    def get_all_by_keyname(self, keyname: str) -> list[AcronymInfo]:
        """Get all occurrences of an acronym.

        Some acronyms appear multiple times with different granularities
        and endpoints.

        Args:
            keyname: The acronym keyname.

        Returns:
            List of AcronymInfo objects, empty list if not found.
        """
        return self._acronyms.get(keyname.upper(), [])

    def get_description(self, keyname: str, endpoint: str | None = None) -> str | None:
        """Get human-readable description for an acronym.

        Args:
            keyname: The acronym keyname.
            endpoint: Optional endpoint name to filter by.

        Returns:
            Description string if found, None otherwise.
        """
        info = self.get(keyname, endpoint)
        return info.description if info else None

    def get_granularity(self, keyname: str, endpoint: str | None = None) -> int | None:
        """Get granularity in minutes for an acronym.

        Args:
            keyname: The acronym keyname.
            endpoint: Optional endpoint name to filter by.

        Returns:
            Granularity in minutes if found, None otherwise.
        """
        info = self.get(keyname, endpoint)
        return info.granularity_minutes if info else None

    def get_endpoint(self, keyname: str, endpoint: str | None = None) -> str | None:
        """Get endpoint name for an acronym.

        Args:
            keyname: The acronym keyname.
            endpoint: Optional endpoint name to filter by (for consistency).

        Returns:
            Endpoint name if found, None otherwise.
        """
        info = self.get(keyname, endpoint)
        return info.endpoint if info else None

    def get_sequence(self, keyname: str, endpoint: str | None = None) -> str | None:
        """Get sequence information for an acronym.

        Args:
            keyname: The acronym keyname.
            endpoint: Optional endpoint name to filter by.

        Returns:
            Sequence string if found, None otherwise.
        """
        info = self.get(keyname, endpoint)
        return info.sequence if info else None

    def get_unit(self, keyname: str, endpoint: str | None = None) -> str | None:
        """Get unit for an acronym.

        Args:
            keyname: The acronym keyname.
            endpoint: Optional endpoint name to filter by.

        Returns:
            Unit string if found, None otherwise.
        """
        info = self.get(keyname, endpoint)
        return info.unit if info else None

    def filter_by_endpoint(self, endpoint: str) -> list[AcronymInfo]:
        """Get all acronyms for a specific endpoint.

        Args:
            endpoint: The endpoint name to filter by.

        Returns:
            List of AcronymInfo objects matching the endpoint.
        """
        result = []
        for acronyms in self._acronyms.values():
            for info in acronyms:
                if info.endpoint == endpoint:
                    result.append(info)
        return result

    def filter_by_granularity(self, granularity_minutes: int) -> list[AcronymInfo]:
        """Get all acronyms with a specific granularity.

        Args:
            granularity_minutes: The granularity in minutes to filter by.

        Returns:
            List of AcronymInfo objects matching the granularity.
        """
        result = []
        for acronyms in self._acronyms.values():
            for info in acronyms:
                if info.granularity_minutes == granularity_minutes:
                    result.append(info)
        return result

    def list_all(self) -> list[AcronymInfo]:
        """Get all acronym information.

        Returns:
            List of all AcronymInfo objects (includes duplicates).
        """
        result = []
        for acronyms in self._acronyms.values():
            result.extend(acronyms)
        return result

    def list_keynames(self) -> list[str]:
        """Get all unique acronym keynames.

        Returns:
            List of all unique acronym keynames.
        """
        return list(self._acronyms.keys())


# Global instance for convenience
_lookup_instance: AcronymLookup | None = None


def get_lookup() -> AcronymLookup:
    """Get the global AcronymLookup instance.

    Returns:
        The global AcronymLookup instance.
    """
    global _lookup_instance
    if _lookup_instance is None:
        _lookup_instance = AcronymLookup()
    return _lookup_instance


# Convenience functions that use the global instance
def get_acronym_info(keyname: str, endpoint: str | None = None) -> AcronymInfo | None:
    """Get information for a specific acronym.

    Args:
        keyname: The acronym keyname (e.g., "BLTRAMT").
        endpoint: Optional endpoint name to filter by.

    Returns:
        AcronymInfo if found, None otherwise.
    """
    return get_lookup().get(keyname, endpoint)


def get_all_acronym_info(keyname: str) -> list[AcronymInfo]:
    """Get all occurrences of an acronym.

    Some acronyms appear multiple times with different granularities
    and endpoints.

    Args:
        keyname: The acronym keyname.

    Returns:
        List of AcronymInfo objects, empty list if not found.
    """
    return get_lookup().get_all_by_keyname(keyname)


def get_acronym_description(keyname: str, endpoint: str | None = None) -> str | None:
    """Get human-readable description for an acronym.

    Args:
        keyname: The acronym keyname.
        endpoint: Optional endpoint name to filter by.

    Returns:
        Description string if found, None otherwise.
    """
    return get_lookup().get_description(keyname, endpoint)


def get_acronym_granularity(keyname: str, endpoint: str | None = None) -> int | None:
    """Get granularity in minutes for an acronym.

    Args:
        keyname: The acronym keyname.
        endpoint: Optional endpoint name to filter by.

    Returns:
        Granularity in minutes if found, None otherwise.
    """
    return get_lookup().get_granularity(keyname, endpoint)


def get_acronym_endpoint(keyname: str, endpoint: str | None = None) -> str | None:
    """Get endpoint name for an acronym.

    Args:
        keyname: The acronym keyname.
        endpoint: Optional endpoint name to filter by (for consistency).

    Returns:
        Endpoint name if found, None otherwise.
    """
    return get_lookup().get_endpoint(keyname, endpoint)


def get_acronym_unit(keyname: str, endpoint: str | None = None) -> str | None:
    """Get unit for an acronym.

    Args:
        keyname: The acronym keyname.
        endpoint: Optional endpoint name to filter by.

    Returns:
        Unit string if found, None otherwise.
    """
    return get_lookup().get_unit(keyname, endpoint)


def get_acronyms_by_endpoint(endpoint: str) -> list[AcronymInfo]:
    """Get all acronyms for a specific endpoint.

    Args:
        endpoint: The endpoint name to filter by.

    Returns:
        List of AcronymInfo objects matching the endpoint.
    """
    return get_lookup().filter_by_endpoint(endpoint)


def get_acronyms_by_granularity(granularity_minutes: int) -> list[AcronymInfo]:
    """Get all acronyms with a specific granularity.

    Args:
        granularity_minutes: The granularity in minutes to filter by.

    Returns:
        List of AcronymInfo objects matching the granularity.
    """
    return get_lookup().filter_by_granularity(granularity_minutes)
