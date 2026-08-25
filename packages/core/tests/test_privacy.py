from datetime import UTC, datetime
from uuid import UUID

from autonomous_career_engine.core.models.candidate import GeneratedSummary
from autonomous_career_engine.core.models.common import (
    ExportPermission,
    PrivacyClassification,
)
from autonomous_career_engine.core.models.evidence import (
    EvidenceBackedValue,
    EvidenceKind,
    EvidenceRecord,
    VerificationStatus,
    effective_export_permission,
)

EVIDENCE_ID = UUID("10000000-0000-4000-8000-000000000001")


def test_effective_export_uses_most_restrictive_policy() -> None:
    value = EvidenceBackedValue[str](
        value="Python",
        evidence_ids=(EVIDENCE_ID,),
        privacy=PrivacyClassification.INTERNAL,
        export_permission=ExportPermission.ALLOWED,
    )
    record = EvidenceRecord(
        evidence_id=EVIDENCE_ID,
        kind=EvidenceKind.CERTIFICATION,
        statement="Example certification",
        issuer="Example Credential Lab",
        verification_status=VerificationStatus.SOURCE_VERIFIED,
        privacy=PrivacyClassification.PRIVATE,
        export_permission=ExportPermission.REVIEW_REQUIRED,
        created_at=datetime(2026, 8, 24, 16, 0, tzinfo=UTC),
    )
    assert (
        effective_export_permission(value, {EVIDENCE_ID: record})
        is ExportPermission.REVIEW_REQUIRED
    )


def test_restricted_evidence_prohibits_export() -> None:
    value = EvidenceBackedValue[str](value="Sensitive fact", evidence_ids=(EVIDENCE_ID,))
    record = EvidenceRecord(
        evidence_id=EVIDENCE_ID,
        kind=EvidenceKind.USER_ATTESTATION,
        statement="Sensitive fact",
        privacy=PrivacyClassification.RESTRICTED,
        export_permission=ExportPermission.PROHIBITED,
        created_at=datetime(2026, 8, 24, 16, 0, tzinfo=UTC),
    )
    assert effective_export_permission(value, {EVIDENCE_ID: record}) is ExportPermission.PROHIBITED


def test_disputed_evidence_prohibits_export() -> None:
    value = EvidenceBackedValue[str](value="Disputed fact", evidence_ids=(EVIDENCE_ID,))
    record = EvidenceRecord(
        evidence_id=EVIDENCE_ID,
        kind=EvidenceKind.REFERENCE,
        statement="Disputed fact",
        verification_status=VerificationStatus.DISPUTED,
        export_permission=ExportPermission.ALLOWED,
        created_at=datetime(2026, 8, 24, 16, 0, tzinfo=UTC),
    )
    assert effective_export_permission(value, {EVIDENCE_ID: record}) is ExportPermission.PROHIBITED


def test_disputed_evidence_prohibits_generated_summary_export() -> None:
    summary = GeneratedSummary(text="Synthetic summary.", evidence_ids=(EVIDENCE_ID,))
    record = EvidenceRecord(
        evidence_id=EVIDENCE_ID,
        kind=EvidenceKind.REFERENCE,
        statement="Disputed source for a synthetic summary.",
        verification_status=VerificationStatus.DISPUTED,
        export_permission=ExportPermission.ALLOWED,
        created_at=datetime(2026, 8, 24, 16, 0, tzinfo=UTC),
    )

    assert (
        effective_export_permission(summary, {EVIDENCE_ID: record})
        is ExportPermission.PROHIBITED
    )


def test_restricted_evidence_prohibits_generated_summary_export() -> None:
    summary = GeneratedSummary(text="Synthetic summary.", evidence_ids=(EVIDENCE_ID,))
    record = EvidenceRecord(
        evidence_id=EVIDENCE_ID,
        kind=EvidenceKind.USER_ATTESTATION,
        statement="Restricted source for a synthetic summary.",
        privacy=PrivacyClassification.RESTRICTED,
        export_permission=ExportPermission.PROHIBITED,
        created_at=datetime(2026, 8, 24, 16, 0, tzinfo=UTC),
    )

    assert (
        effective_export_permission(summary, {EVIDENCE_ID: record})
        is ExportPermission.PROHIBITED
    )


def test_evidence_free_generated_summary_requires_export_review() -> None:
    summary = GeneratedSummary(text="Synthetic summary.")

    assert effective_export_permission(summary, {}) is ExportPermission.REVIEW_REQUIRED
