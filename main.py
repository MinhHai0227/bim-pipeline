from pathlib import Path
import ifcopenshell
import ifcopenshell.util
import ifcopenshell.util.element
import json


class IFCProcessor:
    def __init__(self, ifc_path):
        self.ifc = ifcopenshell.open(str(ifc_path))

    def extract_location(self, element):
        """Extract floor and room information from an element"""
        floor = None
        room = None
        
        # Try to get floor from StoreyName or similar properties
        if hasattr(element, "Name"):
            floor = getattr(element, "Name", None)
        
        return floor, room

    def extract_elements(self):
        """Extract all elements from IFC file"""
        result = []

        for element in self.ifc.by_type("IfcProduct"):
            if not hasattr(element, "GlobalId"):
                continue

            ifc_class = element.is_a()

            # Bỏ các object không phải asset vận hành nếu muốn
            if ifc_class in ["IfcOpeningElement", "IfcAnnotation"]:
                continue

            psets = ifcopenshell.util.element.get_psets(element)

            type_obj = ifcopenshell.util.element.get_type(element)
            type_name = getattr(type_obj, "Name", None) if type_obj else None

            floor, room = self.extract_location(element)

            item = {
                "global_id": element.GlobalId,
                "ifc_class": ifc_class,
                "name": getattr(element, "Name", None),
                "type": type_name,
                "floor": floor,
                "room": room,
                "psets": psets,
            }

            result.append(item)

        return result


if __name__ == "__main__":
    project_dir = Path(__file__).resolve().parent
    ifc_path = project_dir / "data" / "Ifc2x3_Duplex_Mechanical.ifc"
    
    processor = IFCProcessor(ifc_path)
    elements = processor.extract_elements()
    
    # Save to JSON file
    output_file = project_dir / "output.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(elements, f, indent=2, ensure_ascii=False)
    
    print(f"Found {len(elements)} elements")
    print(f"Results saved to: {output_file}")


