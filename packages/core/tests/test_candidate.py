from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from autonomous_career_engine.core.models.candidate import CandidateProfile, Skill
from autonomous_career_engine.core.models.common import ContentOrigin, ProfileValue
from autonomous_career_engine.core.models.evidence import (
    EvidenceBackedValue,
    EvidenceKind,
    EvidenceRecord,
)

CANDIDATE_ID = UUID("00000000-0000-4000-8000-000000000001")
EVIDENCE_ID = UUID("10000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 8, 24, 16, 0, tzinfo=UTC)


def valid_profile() -> CandidateProfile:
    return CandidateProfile(
        candidate_id=CANDIDATE_ID,
        contact={"full_name": ProfileValue[str](value="Avery Example")},
        skills=[
            Skill(
                skill_id=UUID("20000000-0000-4000-8000-000000000001"),
                name=EvidenceBackedValue[str](value="Python", evidence_ids=[EVIDENCE_ID]),
            )
        ],
        evidence=[
            EvidenceRecord(
                evidence_id=EVIDENCE_ID,
                kind=EvidenceKind.USER_ATTESTATION,
                statement="Avery uses Python in fictional portfolio projects.",
                created_at=NOW,
            )
        ],
        created_at=NOW,
        updated_at=NOW,
    )


def test_candidate_profile_round_trips() -> None:
    profile = valid_profile()
    assert CandidateProfile.model_validate_json(profile.model_dump_json()) == profile


def test_candidate_profile_rejects_missing_evidence() -> None:
    data = valid_profile().model_dump(mode="json")
    data["evidence"] = []
    with pytest.raises(ValidationError, match=str(EVIDENCE_ID)):
        CandidateProfile.model_validate(data)


def test_candidate_profile_rejects_duplicate_evidence_ids() -> None:
    data = valid_profile().model_dump(mode="json")
    data["evidence"].append(data["evidence"][0])
    with pytest.raises(ValidationError, match="duplicate evidence IDs"):
        CandidateProfile.model_validate(data)


def test_generated_summary_is_always_ai_generated() -> None:
    data = valid_profile().model_dump(mode="json")
    data["generated_summaries"] = [
        {
            "text": "Synthetic generated summary.",
            "origin": ContentOrigin.SOURCE,
            "evidence_ids": [str(EVIDENCE_ID)],
        }
    ]
    with pytest.raises(ValidationError, match="ai_generated"):
        CandidateProfile.model_validate(data)


def test_restricted_generated_summary_must_prohibit_export() -> None:
    data = valid_profile().model_dump(mode="json")
    data["generated_summaries"] = [
        {
            "text": "Sensitive synthetic summary.",
            "privacy": "restricted",
            "export_permission": "review_required",
        }
    ]
    with pytest.raises(ValidationError, match="restricted summaries must prohibit export"):
        CandidateProfile.model_validate(data)


def test_candidate_aggregate_collections_cannot_be_mutated() -> None:
    profile = valid_profile()

    with pytest.raises(AttributeError):
        profile.evidence.clear()  # type: ignore[attr-defined]
    with pytest.raises(AttributeError):
        profile.skills.append(profile.skills[0])  # type: ignore[attr-defined]

    assert len(profile.evidence) == 1
    assert len(profile.skills) == 1


def test_candidate_collection_tuples_serialize_as_json_arrays() -> None:
    profile = valid_profile()

    dumped = profile.model_dump(mode="json")
    assert isinstance(dumped["evidence"], list)
    assert isinstance(dumped["skills"], list)
