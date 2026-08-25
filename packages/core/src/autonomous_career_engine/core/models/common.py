from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Generic, TypeVar

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    model_validator,
)
from pydantic.json_schema import JsonDict

NonBlankStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, pattern=r"\S"),
]
Confidence = Annotated[Decimal, Field(ge=0, le=1)]
WebUrl = Annotated[
    HttpUrl,
    Field(json_schema_extra={"pattern": r"^[Hh][Tt][Tt][Pp][Ss]?://"}),
]


def _require_timezone(value: datetime) -> datetime:
    if value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value


AwareDateTime = Annotated[datetime, AfterValidator(_require_timezone)]


def restricted_export_schema() -> JsonDict:
    return {
        "if": {
            "properties": {"privacy": {"const": PrivacyClassification.RESTRICTED.value}},
            "required": ["privacy"],
        },
        "then": {
            "properties": {"export_permission": {"const": ExportPermission.PROHIBITED.value}},
            "required": ["export_permission"],
        },
    }


def ai_generated_review_schema() -> JsonDict:
    return {
        "if": {
            "properties": {"origin": {"const": ContentOrigin.AI_GENERATED.value}},
            "required": ["origin"],
        },
        "then": {
            "not": {
                "properties": {"export_permission": {"const": ExportPermission.ALLOWED.value}},
                "required": ["export_permission"],
            }
        },
    }


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PrivacyClassification(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    PRIVATE = "private"
    RESTRICTED = "restricted"


class ExportPermission(StrEnum):
    ALLOWED = "allowed"
    REVIEW_REQUIRED = "review_required"
    PROHIBITED = "prohibited"


class ContentOrigin(StrEnum):
    SOURCE = "source"
    USER = "user"
    DERIVED = "derived"
    AI_GENERATED = "ai_generated"


class DateRange(ContractModel):
    start: date
    end: date | None = None

    @model_validator(mode="after")
    def validate_order(self) -> "DateRange":
        if self.end is not None and self.end < self.start:
            raise ValueError("date range end cannot precede start")
        return self


ValueT = TypeVar("ValueT")


class ProfileValue(ContractModel, Generic[ValueT]):
    model_config = ConfigDict(
        json_schema_extra={
            "allOf": [restricted_export_schema(), ai_generated_review_schema()],
        }
    )

    value: ValueT
    origin: ContentOrigin = ContentOrigin.USER
    privacy: PrivacyClassification = PrivacyClassification.PRIVATE
    export_permission: ExportPermission = ExportPermission.REVIEW_REQUIRED

    @model_validator(mode="after")
    def validate_policy(self) -> "ProfileValue[ValueT]":
        if (
            self.privacy is PrivacyClassification.RESTRICTED
            and self.export_permission is not ExportPermission.PROHIBITED
        ):
            raise ValueError("restricted values must prohibit export")
        if (
            self.origin is ContentOrigin.AI_GENERATED
            and self.export_permission is ExportPermission.ALLOWED
        ):
            raise ValueError("AI-generated values require review before export")
        return self
