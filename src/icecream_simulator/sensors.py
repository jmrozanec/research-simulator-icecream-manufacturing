"""
Sensor model — turn a clean simulated value into a realistic reading.

A ``SensorSpec`` captures what an instrument datasheet would tell you: accuracy
(absolute, % of full scale, or % of rate), measurement range, sampling rate,
bias, drift, and dropout probability. Each spec carries a ``Provenance`` so a
downstream researcher can audit where the number came from.

``sample_reading`` applies the spec to a ground-truth value and returns a
``SensorReading`` carrying both the observation and the truth. Keeping the
truth lets ML pipelines train on (reading, truth) pairs and weight losses by
the per-reading sigma, which is the right way to handle heteroscedastic
measurement noise.
"""

from __future__ import annotations

import math
import random
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from icecream_simulator.provenance import Provenance


class AccuracyKind(str, Enum):
    """How to interpret the ``accuracy`` field of a SensorSpec."""

    ABS = "abs"           # absolute units, e.g. ±0.15 °C
    REL_FS = "rel_fs"     # fraction of (range_max - range_min)
    REL_RATE = "rel_rate" # fraction of |value|


class SensorSpec(BaseModel):
    """Instrument-class specification for one sensor channel.

    Defaults below the model are intentionally absent — every sensor in a plant
    profile must declare its own values and provenance. Use the
    ``pt100_class_a`` / ``mag_flowmeter`` / ``piezoresistive_pressure`` helpers
    in ``plant_profile`` for vendor-anchored starting points.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Unique tag, e.g. 'TT-101' or 'pasteurization.mix_out_T'")
    measurand: str = Field(
        description="What is measured: 'temperature' | 'pressure' | 'flow' | "
                    "'level' | 'motor_current' | 'speed' | 'viscosity' | "
                    "'conductivity' | 'ph' | 'turbidity' | 'concentration' | "
                    "'ice_crystal_size' | 'd32' | 'log10_reduction' | 'overrun' | other"
    )
    unit: str
    accuracy: float = Field(gt=0)
    accuracy_kind: AccuracyKind = AccuracyKind.ABS
    range_min: float
    range_max: float
    sampling_hz: float = Field(default=1.0, gt=0)
    bias: float = Field(default=0.0, description="Systematic offset in measurand units")
    drift_per_hour: float = Field(default=0.0, description="Drift of the bias over time")
    dropout_prob: float = Field(default=0.0, ge=0.0, le=1.0)
    provenance: Provenance

    def sigma_for(self, value: float) -> float:
        """Return the 1-sigma noise standard deviation at this value."""
        if self.accuracy_kind == AccuracyKind.ABS:
            return abs(self.accuracy)
        if self.accuracy_kind == AccuracyKind.REL_FS:
            return abs(self.accuracy) * (self.range_max - self.range_min)
        if self.accuracy_kind == AccuracyKind.REL_RATE:
            return abs(self.accuracy) * abs(value)
        return 0.0


class SensorReading(BaseModel):
    """One observation: the noisy value plus its ground truth and uncertainty."""

    name: str
    measurand: str
    unit: str
    value: float = Field(description="Observed (with noise + bias)")
    truth: float = Field(description="Ground truth before noise")
    sigma: float = Field(description="1-sigma uncertainty at this point")
    bias: float = 0.0
    dropped: bool = False
    out_of_range: bool = False
    timestamp_s: float | None = None


def sample_reading(
    spec: SensorSpec,
    truth: float,
    rng: random.Random,
    *,
    elapsed_hours: float = 0.0,
    timestamp_s: float | None = None,
) -> SensorReading:
    """Apply noise + bias + drift + dropout to ``truth`` per ``spec``.

    ``elapsed_hours`` scales the drift term; pass 0 for an instantaneous read.
    NaN-truth inputs produce a dropped reading rather than propagating NaN.
    """
    if truth is None or not math.isfinite(truth):
        return SensorReading(
            name=spec.name, measurand=spec.measurand, unit=spec.unit,
            value=float("nan"), truth=float("nan"),
            sigma=0.0, bias=0.0, dropped=True, timestamp_s=timestamp_s,
        )

    sigma = spec.sigma_for(truth)
    current_bias = spec.bias + spec.drift_per_hour * elapsed_hours

    if spec.dropout_prob > 0.0 and rng.random() < spec.dropout_prob:
        return SensorReading(
            name=spec.name, measurand=spec.measurand, unit=spec.unit,
            value=float("nan"), truth=float(truth),
            sigma=sigma, bias=current_bias,
            dropped=True, timestamp_s=timestamp_s,
        )

    noise = rng.gauss(0.0, sigma) if sigma > 0 else 0.0
    noisy = float(truth) + current_bias + noise
    out_of_range = (noisy < spec.range_min) or (noisy > spec.range_max)
    clipped = min(max(noisy, spec.range_min), spec.range_max)
    return SensorReading(
        name=spec.name, measurand=spec.measurand, unit=spec.unit,
        value=clipped, truth=float(truth),
        sigma=sigma, bias=current_bias,
        dropped=False, out_of_range=out_of_range,
        timestamp_s=timestamp_s,
    )


__all__ = ["AccuracyKind", "SensorSpec", "SensorReading", "sample_reading"]
