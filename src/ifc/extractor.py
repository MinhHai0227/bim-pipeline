from __future__ import annotations

from pathlib import Path
from typing import Any

import ifcopenshell
import ifcopenshell.util.element

from src.ifc.asset_rules import SKIP_IFC_CLASSES


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]

    return str(value)


def _get_express_id(element) -> int | None:
    try:
        return int(element.id())
    except (TypeError, ValueError, AttributeError):
        return None


def _normalized_property_name(name: str) -> str:
    return "".join(char.lower() for char in name if char.isalnum())


class IFCExtractor:
    DIGITAL_TWIN_PSET_NAMES = [
        "DT.Common",
        "DT.HVAC",
        "DT.LV",
        "DT.HV",
        "DT.EMG",
        "DT.Boiler",
        "DT.FS",
        "DT.UPS",
        "DT.Lighting",
        "DT.CCTV",
        "DT.IoT",
        "DT.MedicalGas",
        "DT.Plumbing",
        "DT.Drainage",
        "DT.LIFT",
        "DT.EL",
        "DT.Filtration",
        "DT.Security",
    ]

    PROPERTY_ALIASES = {
        "asset_identifier": [
            "AssetIdentifier",
            "Asset ID",
            "AssetId",
            "AssetTag",
            "Asset Code",
            "DT.Common.Asset Code",
        ],
        "asset_tag": [
            "Asset Tag",
            "Asset Tag No.",
            "Tag No.",
            "DT.Common.Asset Tag No.",
            "DT.Common.Zone Tag No.",
        ],
        "description": [
            "Description",
            "Equipment Description",
            "DT.Common.Equipment Description",
        ],
        "equipment_location": [
            "Equipment Location",
            "Functional Location",
            "DT.HVAC.Equipment Location",
            "DT.Common.Functional Location",
        ],
        "equipment_type": [
            "Equipment Type",
            "Asset Type",
            "DT.HVAC.Equipment Type",
        ],
        "functional_location": [
            "Functional Location",
            "DT.Common.Functional Location",
        ],
        "manufacturer": [
            "Manufacturer",
            "ManufacturerName",
            "DT.Common.Manufacturer",
        ],
        "model": [
            "ModelReference",
            "Model",
            "ModelNumber",
            "Model No.",
            "Type Mark",
            "DT.Common.Model No.",
        ],
        "reference": ["Reference", "Type Mark", "Mark", "DT.Common.Grouped Equipment ID"],
        "serial_number": [
            "SerialNumber",
            "Serial Number",
            "Serial No.",
            "Serial",
            "DT.Common.Serial Number",
        ],
        "status": ["Status", "Phase Created", "Asset Status", "DT.Common.Asset Status"],
        "system_name": [
            "System",
            "SystemName",
            "System Name",
            "Discipline",
            "DT.Common.System",
            "DT.Common.Functional Location",
        ],
    }

    QUANTITY_ALIASES = {
        "area": [
            "Area",
            "GrossArea",
            "GrossFootprintArea",
            "GrossSideArea",
            "NetArea",
            "NetFootprintArea",
            "NetSideArea",
        ],
        "height": ["Height", "GrossHeight", "NetHeight", "NominalHeight"],
        "length": ["Length", "GrossLength", "NetLength", "NominalLength"],
        "volume": ["Volume", "GrossVolume", "NetVolume"],
        "weight": ["Weight", "GrossWeight", "NetWeight"],
        "width": ["Width", "GrossWidth", "NetWidth", "NominalWidth"],
    }

    def __init__(self, ifc_path: str | Path) -> None:
        self.ifc_path = Path(ifc_path)
        self.ifc = ifcopenshell.open(str(self.ifc_path))

    @property
    def schema_name(self) -> str:
        return str(getattr(self.ifc, "schema", "") or "")

    def iter_products(self):
        for element in self.ifc.by_type("IfcProduct"):
            if element.is_a() not in SKIP_IFC_CLASSES:
                yield element

    def extract_location(self, element) -> tuple[str | None, str | None]:
        floor = None
        room = None

        container = ifcopenshell.util.element.get_container(element)
        if container:
            if container.is_a("IfcBuildingStorey"):
                floor = container.Name
            elif container.is_a("IfcSpace"):
                room = container.Name
                storey = ifcopenshell.util.element.get_container(container)
                if storey and storey.is_a("IfcBuildingStorey"):
                    floor = storey.Name

        return floor, room

    def extract_material(self, element):
        material = ifcopenshell.util.element.get_material(element)
        if not material:
            return None

        material_type = material.is_a()
        if material_type == "IfcMaterial":
            return material.Name

        if material_type == "IfcMaterialLayerSetUsage":
            material = material.ForLayerSet
            material_type = "IfcMaterialLayerSet"

        if material_type == "IfcMaterialLayerSet":
            return [
                layer.Material.Name
                for layer in material.MaterialLayers
                if layer.Material and layer.Material.Name
            ] or None

        if material_type == "IfcMaterialConstituentSet":
            return [
                constituent.Material.Name
                for constituent in material.MaterialConstituents
                if constituent.Material and constituent.Material.Name
            ] or None

        if material_type == "IfcMaterialList":
            return [item.Name for item in material.Materials if item.Name] or None

        return str(material)

    def get_standard_common_pset_name(self, element) -> str | None:
        ifc_class = element.is_a()
        if not ifc_class.startswith("Ifc"):
            return None

        return f"Pset_{ifc_class[3:]}Common"

    def iter_psets(self, psets: dict, preferred_pset_names: list[str] | None = None):
        preferred_pset_names = preferred_pset_names or []

        for pset_name in preferred_pset_names:
            pset = psets.get(pset_name)
            if isinstance(pset, dict):
                yield pset

        for pset_name, pset in psets.items():
            if pset_name not in preferred_pset_names and isinstance(pset, dict):
                yield pset

    def is_meaningful_value(self, name: str, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str) and not value.strip():
            return False
        if isinstance(value, str) and value == name:
            return False

        return True

    def get_pset_value(self, pset: dict, name: str):
        value = pset.get(name)
        if self.is_meaningful_value(name, value):
            return value

        normalized_name = _normalized_property_name(name)
        for key, candidate in pset.items():
            if _normalized_property_name(str(key)) == normalized_name:
                if self.is_meaningful_value(str(key), candidate):
                    return candidate

        return None

    def get_first_value(
        self,
        psets: dict,
        names: list[str],
        preferred_pset_names: list[str] | None = None,
    ):
        for pset in self.iter_psets(psets, preferred_pset_names):
            for name in names:
                value = self.get_pset_value(pset, name)
                if value is not None:
                    return _jsonable(value)

        return None

    def get_first_numeric_value(
        self,
        psets: dict,
        names: list[str],
        preferred_pset_names: list[str] | None = None,
    ):
        for pset in self.iter_psets(psets, preferred_pset_names):
            for name in names:
                value = self.get_pset_value(pset, name)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    return value

        return None

    def extract_custom_properties(self, element, raw_properties: dict) -> dict:
        preferred_psets = [
            self.get_standard_common_pset_name(element),
            *self.DIGITAL_TWIN_PSET_NAMES,
        ]

        return {
            field: self.get_first_value(raw_properties, aliases, preferred_psets)
            for field, aliases in self.PROPERTY_ALIASES.items()
        }

    def extract_element(self, element) -> dict:
        floor, room = self.extract_location(element)
        raw_properties = ifcopenshell.util.element.get_psets(element, psets_only=True) or {}
        raw_quantities = ifcopenshell.util.element.get_psets(element, qtos_only=True) or {}
        quantity_source = {**raw_properties, **raw_quantities}
        quantity_psets = [name for name in raw_quantities if name.startswith("Qto_")]

        return {
            "asset_code": None,
            "express_id": _get_express_id(element),
            "global_id": getattr(element, "GlobalId", None),
            "ifc_class": element.is_a(),
            "name": getattr(element, "Name", None),
            "tag": getattr(element, "Tag", None),
            "floor": floor,
            "room": room,
            "material": _jsonable(self.extract_material(element)),
            "properties": self.extract_custom_properties(element, raw_properties),
            "quantities": {
                field: self.get_first_numeric_value(quantity_source, aliases, quantity_psets)
                for field, aliases in self.QUANTITY_ALIASES.items()
            },
            "raw_properties": _jsonable(raw_properties),
        }
