from datetime import date, datetime

import pytest
from pydantic import ValidationError

from autonomous_career_engine.core.models.common import (
    AwareDateTime,
    ContentOrigin,
    ContractModel,
    DateRange,
    ExportPermission,
    PrivacyClassification,
    ProfileValue,
)


class Observation(ContractModel):
    observed_at: AwareDateTime


def test_profile_value_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="unexpected"):
        ProfileValue[str].model_validate(
            {
                "value": "Data Engineer",
                "origin": "user",
                "privacy": "private",
                "export_permission": "review_required",
                "unexpected": True,
            }
        )


def test_profile_value_rejects_allowed_export_for_restricted_data() -> None:
    with pytest.raises(ValidationError, match="restricted values must prohibit export"):
        ProfileValue[str](
            value="secret",
            origin=ContentOrigin.USER,
            privacy=PrivacyClassification.RESTRICTED,
            export_permission=ExportPermission.ALLOWED,
        )


def test_generated_profile_value_requires_review() -> None:
    with pytest.raises(ValidationError, match="AI-generated values require review"):
        ProfileValue[str](
            value="Generated summary",
            origin=ContentOrigin.AI_GENERATED,
            privacy=PrivacyClassification.INTERNAL,
            export_permission=ExportPermission.ALLOWED,
        )


def test_date_range_rejects_reversed_dates() -> None:
    with pytest.raises(ValidationError, match="cannot precede start"):
        DateRange(start=date(2026, 8, 24), end=date(2026, 8, 23))


def test_observation_timestamp_requires_timezone() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        Observation(observed_at=datetime(2026, 8, 24, 9, 30))


def test_contract_snapshot_rejects_assignment_and_preserves_prior_state() -> None:
    value = ProfileValue[str](value="Original", privacy=PrivacyClassification.INTERNAL)

    with pytest.raises(ValidationError, match="frozen"):
        value.value = "Replacement"

    assert value.value == "Original"


def test_rejected_policy_assignment_does_not_leave_invalid_state() -> None:
    value = ProfileValue[str](
        value="Original",
        privacy=PrivacyClassification.INTERNAL,
        export_permission=ExportPermission.ALLOWED,
    )

    with pytest.raises(ValidationError):
        value.privacy = PrivacyClassification.RESTRICTED

    assert value.privacy is PrivacyClassification.INTERNAL
