import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from autonomous_career_engine.core import CandidateProfile, CanonicalJob

EXAMPLES = Path(__file__).parents[1] / "examples" / "v1"


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def test_valid_examples_validate() -> None:
    CandidateProfile.model_validate(load(EXAMPLES / "candidate-profile.valid.json"))
    CanonicalJob.model_validate(load(EXAMPLES / "canonical-job.valid.json"))


@pytest.mark.parametrize(
    ("model", "filename"),
    [
        (CandidateProfile, "candidate-profile.missing-evidence.json"),
        (CanonicalJob, "canonical-job.missing-provenance.json"),
    ],
)
def test_invalid_examples_fail(
    model: type[CandidateProfile] | type[CanonicalJob], filename: str
) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(load(EXAMPLES / "invalid" / filename))
