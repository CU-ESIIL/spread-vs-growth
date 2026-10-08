"""Minimal dimensional bookkeeping used by tests and claim reports."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Dimensions:
    length: float = 0.0
    time: float = 0.0
    mass: float = 0.0
    energy: float = 0.0
    temperature: float = 0.0

    def __mul__(self, other: "Dimensions") -> "Dimensions":
        return Dimensions(*(a + b for a, b in zip(self.as_tuple(), other.as_tuple(), strict=True)))

    def __truediv__(self, other: "Dimensions") -> "Dimensions":
        return Dimensions(*(a - b for a, b in zip(self.as_tuple(), other.as_tuple(), strict=True)))

    def __pow__(self, exponent: float) -> "Dimensions":
        return Dimensions(*(value * exponent for value in self.as_tuple()))

    def as_tuple(self):
        return self.length, self.time, self.mass, self.energy, self.temperature


LENGTH = Dimensions(length=1)
TIME = Dimensions(time=1)
AREA = LENGTH**2
POWER = Dimensions(energy=1, time=-1)


def perimeter_coefficient_dimensions(sigma: float) -> Dimensions:
    return LENGTH / AREA**sigma


def beta_dimensions(sigma: float) -> Dimensions:
    return AREA ** (1 - sigma) / TIME
