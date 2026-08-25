from collections.abc import Iterator
from typing import Literal
from uuid import UUID

from pydantic import ConfigDict, EmailStr, Field, model_validator

from .common import (
    AwareDateTime,
    ContentOrigin,
    ContractModel,
    DateRange,
    ExportPermission,
    NonBlankStr,
    PrivacyClassification,
    ProfileValue,
    restricted_export_schema,
)
from .evidence import EvidenceBackedValue, EvidenceRecord


class ContactInfo(ContractModel):
    full_name: ProfileValue[NonBlankStr]
    email: ProfileValue[EmailStr] | None = None
    phone: ProfileValue[NonBlankStr] | None = None
    location: ProfileValue[NonBlankStr] | None = None


class WorkExperience(ContractModel):
    experience_id: UUID
    organization: EvidenceBackedValue[NonBlankStr]
    title: EvidenceBackedValue[NonBlankStr]
    dates: EvidenceBackedValue[DateRange]
    highlights: tuple[EvidenceBackedValue[NonBlankStr], ...] = Field(default_factory=tuple)


class Education(ContractModel):
    education_id: UUID
    institution: EvidenceBackedValue[NonBlankStr]
    credential: EvidenceBackedValue[NonBlankStr]
    dates: EvidenceBackedValue[DateRange] | None = None


class Certification(ContractModel):
    certification_id: UUID
    name: EvidenceBackedValue[NonBlankStr]
    issuer: EvidenceBackedValue[NonBlankStr]
    issued_on: EvidenceBackedValue[DateRange] | None = None


class Skill(ContractModel):
    skill_id: UUID
    name: EvidenceBackedValue[NonBlankStr]


class Project(ContractModel):
    project_id: UUID
    name: EvidenceBackedValue[NonBlankStr]
    description: EvidenceBackedValue[NonBlankStr]
    url: EvidenceBackedValue[NonBlankStr] | None = None


class JobPreferences(ContractModel):
    preferred_titles: ProfileValue[tuple[NonBlankStr, ...]] | None = None
    preferred_locations: ProfileValue[tuple[NonBlankStr, ...]] | None = None
    remote_preference: ProfileValue[NonBlankStr] | None = None
    minimum_compensation: ProfileValue[int] | None = None


class GeneratedSummary(ContractModel):
    model_config = ConfigDict(
        json_schema_extra={
            "allOf": [
                restricted_export_schema(),
                {
                    "not": {
                        "properties": {
                            "export_permission": {"const": ExportPermission.ALLOWED.value}
                        },
                        "required": ["export_permission"],
                    }
                },
            ]
        }
    )

    text: NonBlankStr
    origin: Literal[ContentOrigin.AI_GENERATED] = ContentOrigin.AI_GENERATED
    evidence_ids: tuple[UUID, ...] = Field(default_factory=tuple)
    privacy: PrivacyClassification = PrivacyClassification.PRIVATE
    export_permission: ExportPermission = ExportPermission.REVIEW_REQUIRED

    @model_validator(mode="after")
    def validate_export(self) -> "GeneratedSummary":
        if (
            self.privacy is PrivacyClassification.RESTRICTED
            and self.export_permission is not ExportPermission.PROHIBITED
        ):
            raise ValueError("restricted summaries must prohibit export")
        if self.export_permission is ExportPermission.ALLOWED:
            raise ValueError("AI-generated summaries require review")
        return self


def _evidence_references(value: object) -> Iterator[UUID]:
    if isinstance(value, EvidenceBackedValue):
        yield from value.evidence_ids
        return
    if isinstance(value, ContractModel):
        for field_value in value.__dict__.values():
            yield from _evidence_references(field_value)
        return
    if isinstance(value, tuple):
        for item in value:
            yield from _evidence_references(item)


class CandidateProfile(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    candidate_id: UUID
    contact: ContactInfo
    work_experience: tuple[WorkExperience, ...] = Field(default_factory=tuple)
    education: tuple[Education, ...] = Field(default_factory=tuple)
    certifications: tuple[Certification, ...] = Field(default_factory=tuple)
    skills: tuple[Skill, ...] = Field(default_factory=tuple)
    projects: tuple[Project, ...] = Field(default_factory=tuple)
    preferences: JobPreferences | None = None
    generated_summaries: tuple[GeneratedSummary, ...] = Field(default_factory=tuple)
    evidence: tuple[EvidenceRecord, ...] = Field(
        default_factory=tuple,
        json_schema_extra={"uniqueItems": True},
    )
    created_at: AwareDateTime
    updated_at: AwareDateTime

    @model_validator(mode="after")
    def validate_aggregate(self) -> "CandidateProfile":
        evidence_ids = [record.evidence_id for record in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("duplicate evidence IDs")
        known = set(evidence_ids)
        referenced = set(_evidence_references(self))
        referenced.update(
            evidence_id
            for summary in self.generated_summaries
            for evidence_id in summary.evidence_ids
        )
        missing = sorted(referenced - known, key=str)
        if missing:
            raise ValueError(f"missing evidence references: {', '.join(map(str, missing))}")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot precede created_at")
        return self
