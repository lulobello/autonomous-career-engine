from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import ConfigDict, Field, StringConstraints, field_validator, model_validator

from .common import AwareDateTime, Confidence, ContentOrigin, ContractModel, NonBlankStr, WebUrl


class SourceRecord(ContractModel):
    model_config = ConfigDict(
        json_schema_extra={
            "anyOf": [
                {
                    "properties": {"external_id": {"type": "string"}},
                    "required": ["external_id"],
                },
                {
                    "properties": {"source_url": {"type": "string"}},
                    "required": ["source_url"],
                },
            ]
        }
    )

    source_id: UUID
    provider: NonBlankStr
    external_id: NonBlankStr | None = None
    source_url: WebUrl | None = None
    observed_at: AwareDateTime
    terms_url: WebUrl | None = None
    access_restrictions: tuple[NonBlankStr, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_identity(self) -> "SourceRecord":
        if self.external_id is None and self.source_url is None:
            raise ValueError("source requires an external ID or source URL")
        return self


class SourceReference(ContractModel):
    source_id: UUID
    source_field: NonBlankStr | None = None
    observed_at: AwareDateTime | None = None


JobValueT = TypeVar("JobValueT")


class ProvenancedValue(ContractModel, Generic[JobValueT]):
    model_config = ConfigDict(
        json_schema_extra={
            "allOf": [
                {
                    "if": {
                        "properties": {"origin": {"const": ContentOrigin.DERIVED.value}},
                        "required": ["origin"],
                    },
                    "then": {
                        "properties": {"confidence": {"not": {"type": "null"}}},
                        "required": ["confidence"],
                    },
                    "else": {"properties": {"confidence": {"type": "null"}}},
                }
            ]
        }
    )

    value: JobValueT
    sources: Annotated[
        tuple[SourceReference, ...],
        Field(min_length=1, json_schema_extra={"uniqueItems": True}),
    ]
    origin: ContentOrigin = ContentOrigin.SOURCE
    confidence: Confidence | None = None

    @field_validator("sources")
    @classmethod
    def unique_source_references(
        cls, values: tuple[SourceReference, ...]
    ) -> tuple[SourceReference, ...]:
        keys = {(value.source_id, value.source_field, value.observed_at) for value in values}
        if len(keys) != len(values):
            raise ValueError("source references must be unique")
        return values

    @model_validator(mode="after")
    def validate_confidence(self) -> "ProvenancedValue[JobValueT]":
        if self.origin is ContentOrigin.DERIVED and self.confidence is None:
            raise ValueError("derived values require confidence")
        if self.origin is not ContentOrigin.DERIVED and self.confidence is not None:
            raise ValueError("confidence is only valid for derived values")
        return self


class CompensationPeriod(StrEnum):
    HOUR = "hour"
    MONTH = "month"
    YEAR = "year"


CurrencyCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
NonNegativeDecimal = Annotated[
    Decimal,
    Field(
        json_schema_extra={
            "pattern": (
                r"^(?:-?0(?:\.0*)?|(?:0|[1-9][0-9]*)(?:\.[0-9]+)?)"
                r"(?:[Ee][+-]?[0-9]+)?$"
            )
        }
    ),
]


class Compensation(ContractModel):
    model_config = ConfigDict(
        json_schema_extra={
            "anyOf": [
                {
                    "properties": {"minimum": {"not": {"type": "null"}}},
                    "required": ["minimum"],
                },
                {
                    "properties": {"maximum": {"not": {"type": "null"}}},
                    "required": ["maximum"],
                },
            ]
        }
    )

    minimum: NonNegativeDecimal | None = None
    maximum: NonNegativeDecimal | None = None
    currency: CurrencyCode
    period: CompensationPeriod

    @model_validator(mode="after")
    def validate_range(self) -> "Compensation":
        if self.minimum is None and self.maximum is None:
            raise ValueError("compensation requires a minimum or maximum")
        if self.minimum is not None and self.minimum < 0:
            raise ValueError("compensation minimum cannot be negative")
        if self.maximum is not None and self.maximum < 0:
            raise ValueError("compensation maximum cannot be negative")
        if self.minimum is not None and self.maximum is not None and self.maximum < self.minimum:
            raise ValueError("compensation maximum cannot be below minimum")
        return self


CountryCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]


class JobLocation(ContractModel):
    city: NonBlankStr | None = None
    region: NonBlankStr | None = None
    country: CountryCode


class WorkplaceType(StrEnum):
    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE = "remote"
    OTHER = "other"
    UNKNOWN = "unknown"


class EmploymentType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    TEMPORARY = "temporary"
    INTERNSHIP = "internship"
    OTHER = "other"
    UNKNOWN = "unknown"


def _source_references(job: "CanonicalJob") -> Iterator[UUID]:
    for field_name in type(job).model_fields:
        field_value = getattr(job, field_name)
        if isinstance(field_value, ProvenancedValue):
            yield from (reference.source_id for reference in field_value.sources)


class CanonicalJob(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    job_id: UUID
    sources: Annotated[
        tuple[SourceRecord, ...],
        Field(min_length=1, json_schema_extra={"uniqueItems": True}),
    ]
    employer: ProvenancedValue[NonBlankStr]
    title: ProvenancedValue[NonBlankStr]
    description: ProvenancedValue[NonBlankStr] | None = None
    responsibilities: ProvenancedValue[tuple[NonBlankStr, ...]] | None = None
    locations: ProvenancedValue[tuple[JobLocation, ...]] | None = None
    workplace_type: ProvenancedValue[WorkplaceType] | None = None
    employment_type: ProvenancedValue[EmploymentType] | None = None
    compensation: ProvenancedValue[Compensation] | None = None
    requirements: ProvenancedValue[tuple[NonBlankStr, ...]] | None = None
    qualifications: ProvenancedValue[tuple[NonBlankStr, ...]] | None = None
    eligibility_constraints: ProvenancedValue[tuple[NonBlankStr, ...]] | None = None
    application_url: ProvenancedValue[WebUrl] | None = None
    posted_at: ProvenancedValue[date] | None = None
    closing_at: ProvenancedValue[date] | None = None
    posting_observed_at: ProvenancedValue[AwareDateTime] | None = None

    @model_validator(mode="after")
    def validate_aggregate(self) -> "CanonicalJob":
        source_ids = [source.source_id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("duplicate source IDs")
        missing = sorted(set(_source_references(self)) - set(source_ids), key=str)
        if missing:
            raise ValueError(f"missing source references: {', '.join(map(str, missing))}")
        if self.posted_at and self.closing_at and self.closing_at.value < self.posted_at.value:
            raise ValueError("closing date cannot precede posted date")
        return self
