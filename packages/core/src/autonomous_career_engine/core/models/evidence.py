from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Annotated, Generic, Literal, Protocol, TypeVar
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator, model_validator

from .common import (
    AwareDateTime,
    ContentOrigin,
    ContractModel,
    DateRange,
    ExportPermission,
    NonBlankStr,
    PrivacyClassification,
    WebUrl,
    restricted_export_schema,
)


class EvidenceKind(StrEnum):
    USER_ATTESTATION = "user_attestation"
    EMPLOYMENT_RECORD = "employment_record"
    EDUCATION_RECORD = "education_record"
    CERTIFICATION = "certification"
    PORTFOLIO_ARTIFACT = "portfolio_artifact"
    REFERENCE = "reference"


class VerificationStatus(StrEnum):
    SELF_ATTESTED = "self_attested"
    SOURCE_VERIFIED = "source_verified"
    THIRD_PARTY_VERIFIED = "third_party_verified"
    DISPUTED = "disputed"


class EvidenceRecord(ContractModel):
    model_config = ConfigDict(
        json_schema_extra={
            "allOf": [
                restricted_export_schema(),
                {
                    "if": {
                        "properties": {"kind": {"const": EvidenceKind.USER_ATTESTATION.value}},
                        "required": ["kind"],
                    },
                    "then": {
                        "properties": {
                            "verification_status": {
                                "enum": [
                                    VerificationStatus.SELF_ATTESTED.value,
                                    VerificationStatus.DISPUTED.value,
                                ]
                            }
                        }
                    },
                },
                {
                    "if": {
                        "anyOf": [
                            {"not": {"required": ["verification_status"]}},
                            {
                                "properties": {
                                    "verification_status": {
                                        "const": VerificationStatus.SELF_ATTESTED.value
                                    }
                                },
                                "required": ["verification_status"],
                            },
                        ]
                    },
                    "then": {"properties": {"verified_at": {"type": "null"}}},
                },
                {
                    "if": {
                        "properties": {
                            "verification_status": {
                                "enum": [
                                    VerificationStatus.SOURCE_VERIFIED.value,
                                    VerificationStatus.THIRD_PARTY_VERIFIED.value,
                                ]
                            }
                        },
                        "required": ["verification_status"],
                    },
                    "then": {
                        "anyOf": [
                            {
                                "properties": {"issuer": {"type": "string"}},
                                "required": ["issuer"],
                            },
                            {
                                "properties": {"source_url": {"type": "string"}},
                                "required": ["source_url"],
                            },
                        ]
                    },
                },
            ]
        }
    )

    evidence_id: UUID
    kind: EvidenceKind
    statement: NonBlankStr
    issuer: NonBlankStr | None = None
    source_url: WebUrl | None = None
    applicable_dates: DateRange | None = None
    verification_status: VerificationStatus = VerificationStatus.SELF_ATTESTED
    privacy: PrivacyClassification = PrivacyClassification.PRIVATE
    export_permission: ExportPermission = ExportPermission.REVIEW_REQUIRED
    created_at: AwareDateTime
    verified_at: AwareDateTime | None = None

    @model_validator(mode="after")
    def validate_evidence_policy(self) -> "EvidenceRecord":
        if (
            self.privacy is PrivacyClassification.RESTRICTED
            and self.export_permission is not ExportPermission.PROHIBITED
        ):
            raise ValueError("restricted evidence must prohibit export")
        if self.verification_status is VerificationStatus.SELF_ATTESTED and self.verified_at:
            raise ValueError("self-attested evidence cannot have a verification timestamp")
        if self.kind is EvidenceKind.USER_ATTESTATION and self.verification_status not in {
            VerificationStatus.SELF_ATTESTED,
            VerificationStatus.DISPUTED,
        }:
            raise ValueError("user attestation may only be self-attested or disputed")
        if self.verification_status in {
            VerificationStatus.SOURCE_VERIFIED,
            VerificationStatus.THIRD_PARTY_VERIFIED,
        } and self.issuer is None and self.source_url is None:
            raise ValueError("verified evidence requires an issuer or source URL")
        return self


EvidenceValueT = TypeVar("EvidenceValueT")


class EvidencePolicyValue(Protocol):
    @property
    def evidence_ids(self) -> Sequence[UUID]: ...

    @property
    def privacy(self) -> PrivacyClassification: ...

    @property
    def export_permission(self) -> ExportPermission: ...


class EvidenceBackedValue(ContractModel, Generic[EvidenceValueT]):
    model_config = ConfigDict(
        json_schema_extra={"allOf": [restricted_export_schema()]},
    )

    value: EvidenceValueT
    origin: Literal[
        ContentOrigin.SOURCE,
        ContentOrigin.USER,
        ContentOrigin.DERIVED,
    ] = ContentOrigin.USER
    evidence_ids: Annotated[
        tuple[UUID, ...],
        Field(min_length=1, json_schema_extra={"uniqueItems": True}),
    ]
    privacy: PrivacyClassification = PrivacyClassification.PRIVATE
    export_permission: ExportPermission = ExportPermission.REVIEW_REQUIRED

    @field_validator("evidence_ids")
    @classmethod
    def unique_evidence_ids(cls, values: tuple[UUID, ...]) -> tuple[UUID, ...]:
        if len(values) != len(set(values)):
            raise ValueError("evidence references must be unique")
        return values

    @model_validator(mode="after")
    def validate_policy(self) -> "EvidenceBackedValue[EvidenceValueT]":
        if (
            self.privacy is PrivacyClassification.RESTRICTED
            and self.export_permission is not ExportPermission.PROHIBITED
        ):
            raise ValueError("restricted values must prohibit export")
        if self.origin is ContentOrigin.AI_GENERATED:
            raise ValueError("AI-generated content cannot be a factual evidence-backed value")
        return self


def _records_for(
    evidence_ids: Sequence[UUID], evidence_by_id: Mapping[UUID, EvidenceRecord]
) -> list[EvidenceRecord]:
    missing = [evidence_id for evidence_id in evidence_ids if evidence_id not in evidence_by_id]
    if missing:
        raise ValueError(f"missing evidence references: {', '.join(map(str, missing))}")
    return [evidence_by_id[evidence_id] for evidence_id in evidence_ids]


def resolve_verification_status(
    evidence_ids: Sequence[UUID], evidence_by_id: Mapping[UUID, EvidenceRecord]
) -> VerificationStatus:
    if not evidence_ids:
        raise ValueError("at least one evidence reference is required")
    records = _records_for(evidence_ids, evidence_by_id)
    statuses = {record.verification_status for record in records}
    if VerificationStatus.DISPUTED in statuses:
        return VerificationStatus.DISPUTED
    if VerificationStatus.THIRD_PARTY_VERIFIED in statuses:
        return VerificationStatus.THIRD_PARTY_VERIFIED
    if VerificationStatus.SOURCE_VERIFIED in statuses:
        return VerificationStatus.SOURCE_VERIFIED
    return VerificationStatus.SELF_ATTESTED


def effective_export_permission(
    value: EvidencePolicyValue, evidence_by_id: Mapping[UUID, EvidenceRecord]
) -> ExportPermission:
    records = _records_for(value.evidence_ids, evidence_by_id)
    if value.privacy is PrivacyClassification.RESTRICTED:
        return ExportPermission.PROHIBITED
    if any(record.privacy is PrivacyClassification.RESTRICTED for record in records):
        return ExportPermission.PROHIBITED
    if any(record.verification_status is VerificationStatus.DISPUTED for record in records):
        return ExportPermission.PROHIBITED
    permissions = [value.export_permission, *(record.export_permission for record in records)]
    priority = {
        ExportPermission.ALLOWED: 0,
        ExportPermission.REVIEW_REQUIRED: 1,
        ExportPermission.PROHIBITED: 2,
    }
    return max(permissions, key=priority.__getitem__)
