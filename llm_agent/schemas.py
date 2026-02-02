from typing import Optional
from pydantic import BaseModel


class CAF(BaseModel):
    project_sector: Optional[str] = None
    type_of_proposal: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None


class Form1PartA(BaseModel):
    project_activity: Optional[str] = None

    mining_lease_area_ha: Optional[float] = None
    coal_production_mtpA: Optional[float] = None
    sand_extraction_m3_per_year: Optional[float] = None

    proposed_capacity: Optional[float] = None
    existing_capacity: Optional[float] = None

    power_generation_mw: Optional[float] = None
    crushing_capacity_tcd: Optional[float] = None

    road_length_km: Optional[float] = None
    built_up_area_sqm: Optional[float] = None

    hydro_capacity_mw: Optional[float] = None
    dam_height_m: Optional[float] = None

    port_type: Optional[str] = None
    airport_type: Optional[str] = None
    expansion_type: Optional[str] = None


class EnvironmentalSensitivity(BaseModel):
    protected_area_within_10km: Optional[bool] = None
    forest_land_area_ha: Optional[float] = None
    crz_applicable: Optional[bool] = None
    general_condition_applicable: Optional[bool] = None


class RawProjectInput(BaseModel):
    caf: Optional[CAF] = None
    form1_part_a: Optional[Form1PartA] = None
    environmental_sensitivity: Optional[EnvironmentalSensitivity] = None
