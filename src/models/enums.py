from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class IfcFileStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class ValidationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationStage(StrEnum):
    FILE_VALIDATION = "file_validation"
    IFC_PARSE = "ifc_parse"
    SCHEMA_VALIDATION = "schema_validation"
    ASSET_DETECTION = "asset_detection"
    ASSET_VALIDATION = "asset_validation"
