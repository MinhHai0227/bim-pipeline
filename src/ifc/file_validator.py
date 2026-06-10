from pathlib import Path


SUPPORTED_MODEL_FORMATS = {
    ".ifc": "ifc",
    ".rvt": "rvt",
}


class IfcFileValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _safe_filename(filename: str | None) -> str:
    if not filename or not filename.strip():
        raise IfcFileValidationError("FILE_NAME_MISSING", "Uploaded file must have a filename.")

    return Path(filename).name


def validate_model_filename(filename: str | None) -> tuple[str, str]:
    safe_filename = _safe_filename(filename)
    suffix = Path(safe_filename).suffix.lower()
    source_format = SUPPORTED_MODEL_FORMATS.get(suffix)
    if source_format is None:
        raise IfcFileValidationError(
            "FILE_EXTENSION_INVALID",
            "Only .ifc and .rvt files are allowed.",
        )

    return safe_filename, source_format


def validate_ifc_filename(filename: str | None) -> str:
    safe_filename = _safe_filename(filename)
    if Path(safe_filename).suffix.lower() != ".ifc":
        raise IfcFileValidationError("FILE_EXTENSION_INVALID", "Only .ifc files are allowed.")

    return safe_filename


def validate_model_file_size(file_size: int, max_size_bytes: int) -> None:
    if file_size <= 0:
        raise IfcFileValidationError("FILE_EMPTY", "Uploaded model file is empty.")

    if file_size > max_size_bytes:
        raise IfcFileValidationError(
            "FILE_TOO_LARGE",
            f"Uploaded model file exceeds the {max_size_bytes} byte size limit.",
        )


def validate_ifc_file_size(file_size: int, max_size_bytes: int) -> None:
    validate_model_file_size(file_size, max_size_bytes)
