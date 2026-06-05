from pathlib import Path


class IfcFileValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def validate_ifc_filename(filename: str | None) -> str:
    if not filename or not filename.strip():
        raise IfcFileValidationError("FILE_NAME_MISSING", "Uploaded file must have a filename.")

    safe_filename = Path(filename).name
    if Path(safe_filename).suffix.lower() != ".ifc":
        raise IfcFileValidationError("FILE_EXTENSION_INVALID", "Only .ifc files are allowed.")

    return safe_filename


def validate_ifc_file_size(file_size: int, max_size_bytes: int) -> None:
    if file_size <= 0:
        raise IfcFileValidationError("FILE_EMPTY", "Uploaded IFC file is empty.")

    if file_size > max_size_bytes:
        raise IfcFileValidationError(
            "FILE_TOO_LARGE",
            f"Uploaded IFC file exceeds the {max_size_bytes} byte size limit.",
        )
