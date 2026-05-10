from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BatteryConfig:
    capacity_kwh: float
    initial_soc_kwh: float
    min_soc_kwh: float
    max_soc_kwh: float
    max_charge_kw: float
    max_discharge_kw: float
    battery_charge_efficiency: float
    battery_discharge_efficiency: float
    inverter_charge_efficiency: float
    inverter_discharge_efficiency: float

    @property
    def charge_efficiency(self) -> float:
        return self.battery_charge_efficiency * self.inverter_charge_efficiency

    @property
    def discharge_efficiency(self) -> float:
        return self.battery_discharge_efficiency * self.inverter_discharge_efficiency

    def validate(self) -> None:
        if self.capacity_kwh <= 0:
            raise ValueError("Battery capacity must be positive.")
        if not 0 <= self.min_soc_kwh <= self.max_soc_kwh <= self.capacity_kwh:
            raise ValueError("SOC limits must satisfy 0 <= min <= max <= capacity.")
        if not self.min_soc_kwh <= self.initial_soc_kwh <= self.max_soc_kwh:
            raise ValueError("Initial SOC must be within configured SOC limits.")
        if self.max_charge_kw < 0 or self.max_discharge_kw < 0:
            raise ValueError("Charge and discharge power limits must be non-negative.")
        for name, value in (
            ("battery_charge_efficiency", self.battery_charge_efficiency),
            ("battery_discharge_efficiency", self.battery_discharge_efficiency),
            ("inverter_charge_efficiency", self.inverter_charge_efficiency),
            ("inverter_discharge_efficiency", self.inverter_discharge_efficiency),
        ):
            if not 0 < value <= 1:
                raise ValueError(f"{name} must be in the interval (0, 1].")


@dataclass(frozen=True)
class BatteryStep:
    soc_start_kwh: float
    soc_end_kwh: float
    requested_charge_kwh_ac: float
    requested_discharge_kwh_ac: float
    accepted_charge_kwh_ac: float
    delivered_discharge_kwh_ac: float
    stored_charge_kwh_dc: float
    removed_discharge_kwh_dc: float
    blocked_charge_kwh_ac: float
    blocked_discharge_kwh_ac: float


class Battery:
    def __init__(self, config: BatteryConfig) -> None:
        config.validate()
        self.config = config
        self.soc_kwh = config.initial_soc_kwh

    def step(
        self,
        charge_power_kw: float,
        discharge_power_kw: float,
        duration_hours: float,
    ) -> BatteryStep:
        if duration_hours <= 0:
            raise ValueError("Step duration must be positive.")
        if charge_power_kw < 0 or discharge_power_kw < 0:
            raise ValueError("Charge and discharge powers must be non-negative.")
        if charge_power_kw > 0 and discharge_power_kw > 0:
            raise ValueError("Charging and discharging in the same step is not supported.")

        soc_start = self.soc_kwh
        requested_charge_ac = min(charge_power_kw, self.config.max_charge_kw) * duration_hours
        requested_discharge_ac = min(discharge_power_kw, self.config.max_discharge_kw) * duration_hours

        accepted_charge_ac = 0.0
        delivered_discharge_ac = 0.0
        stored_charge_dc = 0.0
        removed_discharge_dc = 0.0

        if requested_charge_ac > 0:
            dc_room = max(self.config.max_soc_kwh - soc_start, 0.0)
            accepted_charge_ac = min(
                requested_charge_ac,
                dc_room / self.config.charge_efficiency,
            )
            stored_charge_dc = accepted_charge_ac * self.config.charge_efficiency
            self.soc_kwh = soc_start + stored_charge_dc

        if requested_discharge_ac > 0:
            dc_available = max(soc_start - self.config.min_soc_kwh, 0.0)
            delivered_discharge_ac = min(
                requested_discharge_ac,
                dc_available * self.config.discharge_efficiency,
            )
            removed_discharge_dc = delivered_discharge_ac / self.config.discharge_efficiency
            self.soc_kwh = soc_start - removed_discharge_dc

        self.soc_kwh = min(max(self.soc_kwh, self.config.min_soc_kwh), self.config.max_soc_kwh)

        return BatteryStep(
            soc_start_kwh=soc_start,
            soc_end_kwh=self.soc_kwh,
            requested_charge_kwh_ac=requested_charge_ac,
            requested_discharge_kwh_ac=requested_discharge_ac,
            accepted_charge_kwh_ac=accepted_charge_ac,
            delivered_discharge_kwh_ac=delivered_discharge_ac,
            stored_charge_kwh_dc=stored_charge_dc,
            removed_discharge_kwh_dc=removed_discharge_dc,
            blocked_charge_kwh_ac=requested_charge_ac - accepted_charge_ac,
            blocked_discharge_kwh_ac=requested_discharge_ac - delivered_discharge_ac,
        )
