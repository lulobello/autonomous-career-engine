from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from autonomous_career_engine.core.models.common import ContentOrigin
from autonomous_career_engine.core.models.job import (
    CanonicalJob,
    Compensation,
    CompensationPeriod,
    ProvenancedValue,
    SourceRecord,
    SourceReference,
)

JOB_ID = UUID("30000000-0000-4000-8000-000000000001")
SOURCE_ID = UUID("40000000-0000-4000-8000-000000000001")
OTHER_SOURCE_ID = UUID("40000000-0000-4000-8000-000000000002")
NOW = datetime(2026, 8, 24, 16, 0, tzinfo=UTC)


def source() -> SourceRecord:
    return SourceRecord(
        source_id=SOURCE_ID,
        provider="synthetic_import",
        external_id="example-job-001",
        source_url="https://jobs.example.com/example-job-001",
        observed_at=NOW,
    )


def sourced(value: str) -> ProvenancedValue[str]:
    return ProvenancedValue[str](
        value=value,
        sources=[SourceReference(source_id=SOURCE_ID, source_field="title")],
    )


def valid_job() -> CanonicalJob:
    return CanonicalJob(
        job_id=JOB_ID,
        sources=[source()],
        employer=sourced("Example Analytics Cooperative"),
        title=sourced("Data Engineer"),
    )


def test_canonical_job_round_trips() -> None:
    job = valid_job()
    assert CanonicalJob.model_validate_json(job.model_dump_json()) == job


def test_provenanced_value_requires_source() -> None:
    with pytest.raises(ValidationError, match="at least 1 item"):
        ProvenancedValue[str](value="Data Engineer", sources=[])


def test_canonical_job_rejects_missing_source_record() -> None:
    data = valid_job().model_dump(mode="json")
    data["sources"][0]["source_id"] = str(OTHER_SOURCE_ID)
    with pytest.raises(ValidationError, match=str(SOURCE_ID)):
        CanonicalJob.model_validate(data)


def test_derived_value_requires_confidence() -> None:
    with pytest.raises(ValidationError, match="derived values require confidence"):
        ProvenancedValue[str](
            value="Data Engineer",
            origin=ContentOrigin.DERIVED,
            sources=[SourceReference(source_id=SOURCE_ID)],
        )


def test_compensation_rejects_reversed_range() -> None:
    with pytest.raises(ValidationError, match="maximum cannot be below minimum"):
        Compensation(
            minimum=Decimal("150000"),
            maximum=Decimal("120000"),
            currency="USD",
            period=CompensationPeriod.YEAR,
        )


def test_source_record_requires_external_identity_or_url() -> None:
    with pytest.raises(ValidationError, match="external ID or source URL"):
        SourceRecord(
            source_id=SOURCE_ID,
            provider="synthetic_import",
            observed_at=NOW,
        )


def test_provenanced_value_rejects_duplicate_source_references() -> None:
    reference = SourceReference(source_id=SOURCE_ID, source_field="title")
    with pytest.raises(ValidationError, match="source references must be unique"):
        ProvenancedValue[str](value="Data Engineer", sources=[reference, reference])


def test_source_value_rejects_confidence() -> None:
    with pytest.raises(ValidationError, match="confidence is only valid for derived values"):
        ProvenancedValue[str](
            value="Data Engineer",
            sources=[SourceReference(source_id=SOURCE_ID)],
            confidence=Decimal("0.8"),
        )


def test_canonical_job_rejects_duplicate_source_ids() -> None:
    data = valid_job().model_dump(mode="json")
    data["sources"].append(data["sources"][0])
    with pytest.raises(ValidationError, match="duplicate source IDs"):
        CanonicalJob.model_validate(data)


def test_canonical_job_rejects_closing_date_before_posted_date() -> None:
    data = valid_job().model_dump(mode="json")
    data["posted_at"] = {
        "value": date(2026, 8, 25).isoformat(),
        "sources": [{"source_id": str(SOURCE_ID)}],
    }
    data["closing_at"] = {
        "value": date(2026, 8, 24).isoformat(),
        "sources": [{"source_id": str(SOURCE_ID)}],
    }
    with pytest.raises(ValidationError, match="closing date cannot precede posted date"):
        CanonicalJob.model_validate(data)


def test_source_collections_cannot_be_mutated() -> None:
    job = valid_job()

    with pytest.raises(AttributeError):
        job.sources.clear()  # type: ignore[attr-defined]
    with pytest.raises(AttributeError):
        job.title.sources.append(job.title.sources[0])  # type: ignore[attr-defined]

    assert len(job.sources) == 1
    assert len(job.title.sources) == 1


def test_source_collection_tuples_serialize_as_json_arrays() -> None:
    job = valid_job()

    dumped = job.model_dump(mode="json")
    assert isinstance(dumped["sources"], list)
    assert isinstance(dumped["title"]["sources"], list)
