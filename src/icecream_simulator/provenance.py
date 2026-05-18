"""
Provenance tags — where every parameter, sensor spec, and default came from.

Every numerical default in a synthetic plant profile carries a Provenance so a
collaborator can decide whether to trust, replace, or fit each one. The point
is honesty about uncertainty: a value sourced from FDA PMO is qualitatively
different from a value marked ``assumption``.

Source kinds and what they typically mean here:

- ``standard``: FDA Grade A PMO, 3-A Sanitary Standards, EHEDG, ISO, Codex.
- ``vendor``:   equipment or instrument datasheet (e.g. PT100 IEC 60751 class A,
                Endress+Hauser Promass Coriolis flowmeter, Tetra Pak A3 freezer).
- ``paper``:    peer-reviewed publication (DOI).
- ``dataset``:  public benchmark or dataset (e.g. Tennessee Eastman, dairy LCA).
- ``fit``:      fitted to in-house experimental data.
- ``assumption``: plausible default, no specific external source.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class SourceKind(str, Enum):
    STANDARD = "standard"
    VENDOR = "vendor"
    PAPER = "paper"
    DATASET = "dataset"
    FIT = "fit"
    ASSUMPTION = "assumption"


class Provenance(BaseModel):
    """Where a value or default came from."""

    model_config = ConfigDict(frozen=True)

    kind: SourceKind
    citation: str = Field(
        description="Citation, DOI, datasheet identifier, or 'n/a' for assumptions",
    )
    note: str = Field(default="", description="Free-text clarification")

    @classmethod
    def assumption(cls, note: str = "") -> "Provenance":
        """Mark a value as a plausible default with no specific source."""
        return cls(kind=SourceKind.ASSUMPTION, citation="n/a", note=note)

    @classmethod
    def standard(cls, citation: str, note: str = "") -> "Provenance":
        return cls(kind=SourceKind.STANDARD, citation=citation, note=note)

    @classmethod
    def vendor(cls, citation: str, note: str = "") -> "Provenance":
        return cls(kind=SourceKind.VENDOR, citation=citation, note=note)

    @classmethod
    def paper(cls, citation: str, note: str = "") -> "Provenance":
        return cls(kind=SourceKind.PAPER, citation=citation, note=note)


__all__ = ["SourceKind", "Provenance"]
