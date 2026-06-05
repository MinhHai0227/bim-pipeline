from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.ifc.asset_rules import ASSET_IFC_CLASSES, ASSET_IFC_GROUPS, ASSET_PROPERTY_SIGNALS


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _contains_property_signal(properties: Mapping[str, Any]) -> bool:
    for value in properties.values():
        if isinstance(value, Mapping):
            for signal in ASSET_PROPERTY_SIGNALS:
                if _has_value(value.get(signal)):
                    return True

    return False


def is_operational_asset(element: Any, raw_properties: Mapping[str, Any]) -> bool:
    ifc_class = element.is_a()

    if ifc_class in ASSET_IFC_CLASSES:
        return True

    for ifc_group in ASSET_IFC_GROUPS:
        if element.is_a(ifc_group):
            return True

    return _contains_property_signal(raw_properties)
