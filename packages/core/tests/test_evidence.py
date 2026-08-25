from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from autonomous_career_engine.core.models.common import ContentOrigin
from autonomous_career_engine.core.models.evidence import (
    EvidenceBackedValue,
    EvidenceKind,
    EvidenceRecord,
    VerificationStatus,
    resolve_verification_status,
)

EVIDENCE_ID = UUID("10000000-0000-4000-8000-000000000001")


def evidence(status: VerificationStatus = VerificationStatus.SELF_ATTESTED) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=EVIDENCE_ID,
        kind=EvidenceKind.USER_ATTESTATION,
        statement="Built a synthetic data-quality pipeline.",
        verification_status=status,
        created_at=datetime(2026, 8, 24, 16, 0, tzinfo=UTC),
    )


def test_evidence_backed_value_requires_reference() -> None:
    with pytest.raises(ValidationError, match="at least 1 item"):
        EvidenceBackedValue[str](value="Python", evidence_ids=[])


def test_duplicate_evidence_references_are_rejected() -> None:
    with pytest.raises(ValidationError, match="evidence references must be unique"):
        EvidenceBackedValue[str](
            value="Python",
            origin=ContentOrigin.USER,
            evidence_ids=[EVIDENCE_ID, EVIDENCE_ID],
        )


def test_disputed_evidence_wins_conservatively() -> None:
    records = {EVIDENCE_ID: evidence(VerificationStatus.DISPUTED)}
    assert resolve_verification_status([EVIDENCE_ID], records) is VerificationStatus.DISPUTED


def test_missing_evidence_reference_fails() -> None:
    with pytest.raises(ValueError, match=str(EVIDENCE_ID)):
        resolve_verification_status([EVIDENCE_ID], {})


def test_verified_evidence_requires_issuer_or_source() -> None:
    with pytest.raises(ValidationError, match="issuer or source URL"):
        EvidenceRecord(
            evidence_id=EVIDENCE_ID,
            kind=EvidenceKind.CERTIFICATION,
            statement="Example certification",
            verification_status=VerificationStatus.SOURCE_VERIFIED,
            created_at=datetime(2026, 8, 24, 16, 0, tzinfo=UTC),
        )


@pytest.mark.parametrize(
    "status",
    [VerificationStatus.SOURCE_VERIFIED, VerificationStatus.THIRD_PARTY_VERIFIED],
)
def test_user_attestation_rejects_verified_statuses(status: VerificationStatus) -> None:
    with pytest.raises(ValidationError, match="user attestation"):
        EvidenceRecord(
            evidence_id=EVIDENCE_ID,
            kind=EvidenceKind.USER_ATTESTATION,
            statement="Synthetic user claim.",
            issuer="Synthetic issuer",
            source_url="https://evidence.example.com/claim",
            verification_status=status,
            created_at=datetime(2026, 8, 24, 16, 0, tzinfo=UTC),
        )


def test_resolving_verification_requires_at_least_one_reference() -> None:
    with pytest.raises(ValueError, match="at least one evidence reference"):
        resolve_verification_status([], {})


def test_evidence_reference_collection_cannot_be_appended() -> None:
    value = EvidenceBackedValue[str](value="Python", evidence_ids=[EVIDENCE_ID])

    with pytest.raises(AttributeError):
        value.evidence_ids.append(EVIDENCE_ID)  # type: ignore[attr-defined]

    assert value.evidence_ids == (EVIDENCE_ID,)


def test_evidence_reference_tuple_serializes_as_a_json_array() -> None:
    value = EvidenceBackedValue[str](value="Python", evidence_ids=[EVIDENCE_ID])

    assert value.model_dump(mode="json")["evidence_ids"] == [str(EVIDENCE_ID)]
