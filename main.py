from pathlib import Path
import ifcopenshell
import ifcopenshell.util.element
import json


class IFCProcessor:
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

    def extract_elements(self):
        SKIP_TYPES = {"IfcOpeningElement", "IfcAnnotation", "IfcVirtualElement"}
        result = []

        for element in self.ifc.by_type("IfcProduct"):
            ifc_class = element.is_a()
            if ifc_class in SKIP_TYPES:
                continue

            floor, room = self.extract_location(element)

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
                "properties": ifcopenshell.util.element.get_psets(element) or {},
            })

        return result


if __name__ == "__main__":
    project_dir = Path(__file__).resolve().parent
    ifc_path    = project_dir / "data" / "Ifc2x3_Duplex_Architecture.ifc"

    processor = IFCProcessor(ifc_path)
    elements  = processor.extract_elements()

    output_file = project_dir / "output.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(elements, f, indent=2, ensure_ascii=False)

    print(f"Found {len(elements)} elements")
    print(f"Saved to: {output_file}")