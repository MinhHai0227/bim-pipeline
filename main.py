from pathlib import Path
import ifcopenshell
import ifcopenshell.util.element
import json

class IFCProcessor:
    PROPERTY_ALIASES = {
        "reference": ["Reference", "Type Mark", "Mark"],
        "is_external": ["IsExternal", "External"],
        "load_bearing": ["LoadBearing", "Structural", "Bearing"],
        "fire_rating": ["FireRating", "Fire Rating"],
        "status": ["Status", "Phase Created"],
    }

    QUANTITY_ALIASES = {
        "length": ["Length", "NetLength", "GrossLength", "NominalLength", "Cut Length"],
        "width": ["Width", "NetWidth", "GrossWidth", "NominalWidth"],
        "height": ["Height", "NetHeight", "GrossHeight", "NominalHeight"],
        "area": [
            "NetArea",
            "GrossArea",
            "Area",
            "NetSideArea",
            "GrossSideArea",
            "NetFootprintArea",
            "GrossFootprintArea",
        ],
        "volume": ["NetVolume", "GrossVolume", "Volume"],
        "weight": ["NetWeight", "GrossWeight", "Weight"],
    }

    def __init__(self, ifc_path):
        self.ifc = ifcopenshell.open(str(ifc_path))

    def extract_location(self, element):
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
        mat = ifcopenshell.util.element.get_material(element)
        if not mat:
            return None

        t = mat.is_a()

        # Single material
        if t == "IfcMaterial":
            return mat.Name

        # Layer set (IFC2x3 phổ biến — tường nhiều lớp)
        if t == "IfcMaterialLayerSetUsage":
            mat = mat.ForLayerSet
            t = "IfcMaterialLayerSet"

        if t == "IfcMaterialLayerSet":
            return [
                layer.Material.Name
                for layer in mat.MaterialLayers
                if layer.Material and layer.Material.Name
            ] or None

        # Constituent set (IFC4)
        if t == "IfcMaterialConstituentSet":
            return [
                c.Material.Name
                for c in mat.MaterialConstituents
                if c.Material and c.Material.Name
            ] or None

        # Material list (fallback)
        if t == "IfcMaterialList":
            return [m.Name for m in mat.Materials if m.Name] or None

        return None

    def get_standard_common_pset_name(self, element):
        ifc_class = element.is_a()
        if not ifc_class.startswith("Ifc"):
            return None

        return f"Pset_{ifc_class[3:]}Common"

    def iter_psets(self, psets, preferred_pset_names=None):
        preferred_pset_names = preferred_pset_names or []

        for pset_name in preferred_pset_names:
            pset = psets.get(pset_name)
            if not isinstance(pset, dict):
                continue
            yield pset

        for pset_name, pset in psets.items():
            if pset_name in preferred_pset_names or not isinstance(pset, dict):
                continue
            yield pset

    def is_meaningful_value(self, name, value):
        if value is None:
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
        if isinstance(value, str) and value == name:
            return False
        return True

    def get_first_value(self, psets, names, default=None, preferred_pset_names=None):
        for pset in self.iter_psets(psets, preferred_pset_names):
            for name in names:
                value = pset.get(name)
                if self.is_meaningful_value(name, value):
                    return value

        return default

    def get_first_numeric_value(self, psets, names, default=None, preferred_pset_names=None):
        for pset in self.iter_psets(psets, preferred_pset_names):
            for name in names:
                value = pset.get(name)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    return value

        return default

    def extract_custom_properties(self, element, raw_properties):
        preferred_psets = [self.get_standard_common_pset_name(element)]

        return {
            field: self.get_first_value(raw_properties, aliases, preferred_pset_names=preferred_psets)
            for field, aliases in self.PROPERTY_ALIASES.items()
        }

    def extract_quantities(self, element, raw_properties):
        raw_quantities = ifcopenshell.util.element.get_psets(element, qtos_only=True) or {}
        quantity_source = {**raw_properties, **raw_quantities}
        quantity_psets = [name for name in raw_quantities if name.startswith("Qto_")]

        return {
            field: self.get_first_numeric_value(
                quantity_source,
                aliases,
                preferred_pset_names=quantity_psets,
            )
            for field, aliases in self.QUANTITY_ALIASES.items()
        }

    def extract_elements(self):
        SKIP_TYPES = {"IfcOpeningElement", "IfcAnnotation", "IfcVirtualElement"}
        result = []

        for element in self.ifc.by_type("IfcProduct"):
            ifc_class = element.is_a()
            if ifc_class in SKIP_TYPES:
                continue

            floor, room = self.extract_location(element)
            raw_properties = ifcopenshell.util.element.get_psets(element, psets_only=True) or {}

            result.append({
                "global_id": element.GlobalId,
                "ifc_class": ifc_class,
                "name":      element.Name,
                "tag":       getattr(element, "Tag", None),
                "location": {
                    "floor": floor,
                    "room":  room,
                },
                "material":   self.extract_material(element),
                "properties": self.extract_custom_properties(element, raw_properties),
                "quantities": self.extract_quantities(element, raw_properties),
                "raw_properties": raw_properties,
            })
            
        return result


if __name__ == "__main__":
    project_dir = Path(__file__).resolve().parent
    ifc_path    = project_dir / "data" / "Ifc2x3_Duplex_Mechanical.ifc"

    processor = IFCProcessor(ifc_path)
    elements  = processor.extract_elements()

    output_file = project_dir / "output.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(elements, f, indent=2, ensure_ascii=False)

    print(f"Found {len(elements)} elements")
    print(f"Saved to: {output_file}")
