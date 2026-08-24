import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import ValidationError

from autonomous_career_engine.core import CandidateProfile, CanonicalJob
from autonomous_career_engine.core.schema import render_schemas

EXAMPLES = Path(__file__).parents[1] / "examples" / "v1"


def load_example(filename: str) -> dict[str, object]:
    return json.loads((EXAMPLES / filename).read_text(encoding="utf-8"))


def schema_validator(filename: str) -> Draft202012Validator:
    schema = json.loads(render_schemas()[filename])
    return Draft202012Validator(schema, format_checker=FormatChecker())


def assert_structurally_invalid(filename: str, instance: object) -> None:
    assert list(schema_validator(filename).iter_errors(instance))


def test_schema_consumer_distinguishes_structural_from_semantic_invalidity() -> None:
    structural = load_example("invalid/canonical-job.missing-provenance.json")
    semantic = load_example("invalid/candidate-profile.missing-evidence.json")

    assert_structurally_invalid("canonical-job.schema.json", structural)
    assert list(schema_validator("candidate-profile.schema.json").iter_errors(semantic)) == []
    with pytest.raises(ValidationError, match="missing evidence references"):
        CandidateProfile.model_validate(semantic)


@pytest.mark.parametrize("status", ["source_verified", "third_party_verified"])
def test_candidate_schema_rejects_verified_user_attestation(status: str) -> None:
    candidate = load_example("candidate-profile.valid.json")
    evidence = candidate["evidence"][0]
    evidence["verification_status"] = status
    evidence["issuer"] = "Synthetic issuer"

    assert_structurally_invalid("candidate-profile.schema.json", candidate)


def test_candidate_schema_rejects_restricted_evidence_without_prohibited_export() -> None:
    candidate = load_example("candidate-profile.valid.json")
    evidence = candidate["evidence"][0]
    evidence["privacy"] = "restricted"
    evidence["export_permission"] = "review_required"

    assert_structurally_invalid("candidate-profile.schema.json", candidate)


def test_candidate_schema_rejects_ai_generated_factual_values() -> None:
    candidate = load_example("candidate-profile.valid.json")
    skill_value = candidate["skills"][0]["name"]
    skill_value["origin"] = "ai_generated"

    assert_structurally_invalid("candidate-profile.schema.json", candidate)


def test_candidate_schema_rejects_duplicate_evidence_references() -> None:
    candidate = load_example("candidate-profile.valid.json")
    skill_value = candidate["skills"][0]["name"]
    skill_value["evidence_ids"].append(skill_value["evidence_ids"][0])

    assert_structurally_invalid("candidate-profile.schema.json", candidate)


def test_candidate_schema_rejects_exact_duplicate_evidence_records() -> None:
    candidate = load_example("candidate-profile.valid.json")
    candidate["evidence"].append(deepcopy(candidate["evidence"][0]))

    assert_structurally_invalid("candidate-profile.schema.json", candidate)


def test_candidate_schema_rejects_verification_timestamp_on_self_attestation() -> None:
    candidate = load_example("candidate-profile.valid.json")
    candidate["evidence"][0]["verified_at"] = "2026-08-24T17:00:00Z"

    assert_structurally_invalid("candidate-profile.schema.json", candidate)


def test_candidate_schema_rejects_verified_evidence_without_an_issuer_or_source() -> None:
    candidate = load_example("candidate-profile.valid.json")
    evidence = candidate["evidence"][0]
    evidence["kind"] = "certification"
    evidence["verification_status"] = "source_verified"

    assert_structurally_invalid("candidate-profile.schema.json", candidate)


def test_candidate_schema_rejects_restricted_profile_value_without_prohibited_export() -> None:
    candidate = load_example("candidate-profile.valid.json")
    full_name = candidate["contact"]["full_name"]
    full_name["privacy"] = "restricted"
    full_name["export_permission"] = "review_required"

    assert_structurally_invalid("candidate-profile.schema.json", candidate)


def test_candidate_schema_rejects_ai_generated_profile_value_with_allowed_export() -> None:
    candidate = load_example("candidate-profile.valid.json")
    full_name = candidate["contact"]["full_name"]
    full_name["origin"] = "ai_generated"
    full_name["export_permission"] = "allowed"

    assert_structurally_invalid("candidate-profile.schema.json", candidate)


def test_candidate_schema_rejects_generated_summary_with_allowed_export() -> None:
    candidate = load_example("candidate-profile.valid.json")
    candidate["generated_summaries"] = [
        {
            "text": "Synthetic summary.",
            "privacy": "private",
            "export_permission": "allowed",
        }
    ]
    assert_structurally_invalid("candidate-profile.schema.json", candidate)


def test_candidate_schema_rejects_blank_evidence_statement() -> None:
    candidate = load_example("candidate-profile.valid.json")
    candidate["evidence"][0]["statement"] = "   "

    assert_structurally_invalid("candidate-profile.schema.json", candidate)


def test_candidate_schema_rejects_non_http_evidence_source_url() -> None:
    candidate = load_example("candidate-profile.valid.json")
    candidate["evidence"][0]["source_url"] = "ftp://evidence.example.com/claim"

    assert_structurally_invalid("candidate-profile.schema.json", candidate)


def test_job_schema_rejects_source_without_external_identity_or_url() -> None:
    job = load_example("canonical-job.valid.json")
    source = job["sources"][0]
    source.pop("external_id")
    source.pop("source_url")

    assert_structurally_invalid("canonical-job.schema.json", job)


def test_job_schema_rejects_duplicate_provenance_references() -> None:
    job = load_example("canonical-job.valid.json")
    references = job["title"]["sources"]
    references.append(deepcopy(references[0]))

    assert_structurally_invalid("canonical-job.schema.json", job)


def test_job_schema_rejects_exact_duplicate_source_records() -> None:
    job = load_example("canonical-job.valid.json")
    job["sources"].append(deepcopy(job["sources"][0]))

    assert_structurally_invalid("canonical-job.schema.json", job)


def test_job_schema_requires_confidence_for_derived_value() -> None:
    job = load_example("canonical-job.valid.json")
    job["title"]["origin"] = "derived"

    assert_structurally_invalid("canonical-job.schema.json", job)


def test_job_schema_rejects_confidence_for_source_value() -> None:
    job = load_example("canonical-job.valid.json")
    job["title"]["confidence"] = "0.8"

    assert_structurally_invalid("canonical-job.schema.json", job)


def test_job_schema_rejects_non_http_source_url() -> None:
    job = load_example("canonical-job.valid.json")
    job["sources"][0]["source_url"] = "ftp://jobs.example.com/example-job-001"

    assert_structurally_invalid("canonical-job.schema.json", job)


def test_job_schema_rejects_blank_normalized_text() -> None:
    job = load_example("canonical-job.valid.json")
    job["title"]["value"] = "   "

    assert_structurally_invalid("canonical-job.schema.json", job)


def test_job_schema_requires_a_compensation_bound() -> None:
    job = load_example("canonical-job.valid.json")
    job["compensation"] = {
        "value": {"currency": "USD", "period": "year"},
        "sources": deepcopy(job["title"]["sources"]),
        "origin": "source",
    }
    assert_structurally_invalid("canonical-job.schema.json", job)


def test_job_schema_rejects_negative_compensation_bound() -> None:
    job = load_example("canonical-job.valid.json")
    job["compensation"] = {
        "value": {"minimum": "-1", "currency": "USD", "period": "year"},
        "sources": deepcopy(job["title"]["sources"]),
        "origin": "source",
    }
    assert_structurally_invalid("canonical-job.schema.json", job)


def test_cross_record_job_reference_remains_a_semantic_validation_rule() -> None:
    job = load_example("canonical-job.valid.json")
    job["sources"][0]["source_id"] = "40000000-0000-4000-8000-000000000099"

    assert list(schema_validator("canonical-job.schema.json").iter_errors(job)) == []
    with pytest.raises(ValidationError, match="missing source references"):
        CanonicalJob.model_validate(job)


def test_cross_value_job_ordering_remains_a_semantic_validation_rule() -> None:
    job = load_example("canonical-job.valid.json")
    sources = deepcopy(job["title"]["sources"])
    job["posted_at"] = {"value": "2026-08-25", "sources": sources, "origin": "source"}
    job["closing_at"] = {
        "value": "2026-08-24",
        "sources": deepcopy(sources),
        "origin": "source",
    }

    assert list(schema_validator("canonical-job.schema.json").iter_errors(job)) == []
    with pytest.raises(ValidationError, match="closing date cannot precede posted date"):
        CanonicalJob.model_validate(job)
