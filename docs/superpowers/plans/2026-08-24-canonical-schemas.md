# Canonical Schemas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the versioned, provenance-aware candidate-profile and canonical-job contracts required by Issue #1, with enforceable privacy policy, generated JSON Schema, synthetic examples, and CI verification.

**Architecture:** Pydantic v2 models in `packages/core` are the single source of truth. Candidate career facts reference local evidence records, job-domain values reference local source records, and deterministic JSON Schema artifacts expose both aggregates to non-Python consumers. Cross-record validators fail closed; focused policy helpers compute verification and export decisions without a database or provider dependency.

**Tech Stack:** Python 3.12+, Pydantic v2, PEP 621 packaging with Hatchling, pytest, Ruff, mypy, GitHub Actions

**Spec:** `docs/superpowers/specs/2026-08-23-canonical-schemas-design.md`

## Global Constraints

- Target Python 3.12 or newer.
- Use Pydantic v2 as a dependency; do not copy upstream code, schemas, fixtures, prompts, or documentation.
- Keep `packages/core` independent of databases, web frameworks, job providers, model providers, renderers, and user interfaces.
- Reject unknown fields throughout all public models.
- Use timezone-aware ISO 8601 timestamps and UUID identifiers.
- Keep candidate contact information private by default and generated content review-required.
- Represent every candidate career fact with at least one evidence reference.
- Represent every present normalized job-domain value with at least one source reference.
- Keep all examples obviously synthetic and use reserved example domains.
- Treat the Python models as authoritative and commit deterministically generated JSON Schema under `packages/core/schemas/v1`.
- Do not add persistence, ranking, document generation, ATS automation, provider-specific payloads, or real candidate data.

## File map

| File | Responsibility |
| --- | --- |
| `packages/core/LICENSE` | Apache-2.0 license text included in built distributions |
| `packages/core/pyproject.toml` | Package metadata, dependency bounds, and local quality-tool configuration |
| `packages/core/src/autonomous_career_engine/core/models/common.py` | Strict base model, constrained primitives, shared enums, date range, and profile-value policy |
| `packages/core/src/autonomous_career_engine/core/models/evidence.py` | Evidence records, evidence-backed values, verification resolution, and effective export policy |
| `packages/core/src/autonomous_career_engine/core/models/candidate.py` | Candidate sections, generated summaries, aggregate reference validation |
| `packages/core/src/autonomous_career_engine/core/models/job.py` | Job source/provenance records, normalized job values, compensation, and aggregate validation |
| `packages/core/src/autonomous_career_engine/core/schema.py` | Public schema registry, deterministic rendering, write/check CLI |
| `packages/core/examples/v1/**` | Small valid and representative invalid JSON records |
| `packages/core/schemas/v1/**` | Generated language-neutral public contracts |
| `packages/core/tests/**` | Unit, aggregate, fixture, and schema-drift tests |
| `.github/workflows/core-ci.yml` | Clean-install, lint, type, test, and schema-drift verification |
| `packages/core/README.md` | Public model usage, regeneration, privacy, and compatibility guidance |
| `README.md`, `CONTRIBUTING.md` | Accurate capability status and contributor commands |

---

### Task 1: Package scaffold and shared contract primitives

**Files:**
- Create: `packages/core/LICENSE`
- Create: `packages/core/pyproject.toml`
- Create: `packages/core/src/autonomous_career_engine/__init__.py`
- Create: `packages/core/src/autonomous_career_engine/core/__init__.py`
- Create: `packages/core/src/autonomous_career_engine/core/models/__init__.py`
- Create: `packages/core/src/autonomous_career_engine/core/models/common.py`
- Create: `packages/core/tests/test_common.py`

**Interfaces:**
- Consumes: none
- Produces: `ContractModel`, `NonBlankStr`, `AwareDateTime`, `Confidence`, `DateRange`, `PrivacyClassification`, `ExportPermission`, `ContentOrigin`, and `ProfileValue[T]`

- [ ] **Step 1: Add a failing test for shared validation and privacy invariants**

Create `packages/core/tests/test_common.py` with:

```python
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
```

- [ ] **Step 2: Run the tests and confirm the package does not exist yet**

Run: `python -m pip install 'pydantic>=2,<3' 'pytest>=8,<9'`

Expected: the two test-only prerequisites install successfully; the complete editable package and development tools are installed in Step 4.

Run: `python -m pytest packages/core/tests/test_common.py -v`

Expected: collection fails with `ModuleNotFoundError: No module named 'autonomous_career_engine'`.

- [ ] **Step 3: Add package metadata and the minimal shared implementation**

Create `packages/core/pyproject.toml`:

```toml
[build-system]
requires = ["hatchling>=1.27,<2"]
build-backend = "hatchling.build"

[project]
name = "autonomous-career-engine-core"
version = "0.1.0"
description = "Canonical contracts and safety policies for Autonomous Career Engine"
readme = "README.md"
requires-python = ">=3.12"
license = "Apache-2.0"
license-files = ["LICENSE"]
authors = [{ name = "Lu Lobello" }]
dependencies = [
  "email-validator>=2,<3",
  "pydantic>=2,<3",
]

[project.optional-dependencies]
dev = [
  "mypy>=1.14,<2",
  "pytest>=8,<9",
  "ruff>=0.9,<1",
]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]
```

Copy the repository's existing Apache-2.0 `LICENSE` verbatim to `packages/core/LICENSE` so source and wheel distributions carry the approved license. Create empty package markers at the three `__init__.py` paths, then create `common.py`:

```python
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Generic, TypeVar

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

NonBlankStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Confidence = Annotated[Decimal, Field(ge=0, le=1)]


def _require_timezone(value: datetime) -> datetime:
    if value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value


AwareDateTime = Annotated[datetime, AfterValidator(_require_timezone)]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class PrivacyClassification(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    PRIVATE = "private"
    RESTRICTED = "restricted"


class ExportPermission(StrEnum):
    ALLOWED = "allowed"
    REVIEW_REQUIRED = "review_required"
    PROHIBITED = "prohibited"


class ContentOrigin(StrEnum):
    SOURCE = "source"
    USER = "user"
    DERIVED = "derived"
    AI_GENERATED = "ai_generated"


class DateRange(ContractModel):
    start: date
    end: date | None = None

    @model_validator(mode="after")
    def validate_order(self) -> "DateRange":
        if self.end is not None and self.end < self.start:
            raise ValueError("date range end cannot precede start")
        return self


ValueT = TypeVar("ValueT")


class ProfileValue(ContractModel, Generic[ValueT]):
    value: ValueT
    origin: ContentOrigin = ContentOrigin.USER
    privacy: PrivacyClassification = PrivacyClassification.PRIVATE
    export_permission: ExportPermission = ExportPermission.REVIEW_REQUIRED

    @model_validator(mode="after")
    def validate_policy(self) -> "ProfileValue[ValueT]":
        if (
            self.privacy is PrivacyClassification.RESTRICTED
            and self.export_permission is not ExportPermission.PROHIBITED
        ):
            raise ValueError("restricted values must prohibit export")
        if (
            self.origin is ContentOrigin.AI_GENERATED
            and self.export_permission is ExportPermission.ALLOWED
        ):
            raise ValueError("AI-generated values require review before export")
        return self
```

- [ ] **Step 4: Install the package and run the focused tests**

Run: `python -m pip install -e './packages/core[dev]'`

Expected: installation succeeds on Python 3.12+.

Run: `python -m pytest packages/core/tests/test_common.py -v`

Expected: 5 tests pass.

- [ ] **Step 5: Run initial static checks**

Run: `python -m ruff check packages/core`

Expected: `All checks passed!`

Run: `python -m mypy packages/core/src`

Expected: `Success: no issues found`.

- [ ] **Step 6: Commit the shared package foundation**

```bash
git add packages/core/LICENSE packages/core/pyproject.toml packages/core/src packages/core/tests/test_common.py
git commit -m "feat(core): add strict contract primitives"
```

---

### Task 2: Evidence records and conservative policy resolution

**Files:**
- Create: `packages/core/src/autonomous_career_engine/core/models/evidence.py`
- Create: `packages/core/tests/test_evidence.py`
- Create: `packages/core/tests/test_privacy.py`

**Interfaces:**
- Consumes: `ContractModel`, `DateRange`, `NonBlankStr`, `AwareDateTime`, `ContentOrigin`, `PrivacyClassification`, and `ExportPermission`
- Produces: `EvidenceKind`, `VerificationStatus`, `EvidenceRecord`, `EvidenceBackedValue[T]`, `resolve_verification_status(ids, evidence_by_id)`, and `effective_export_permission(value, evidence_by_id)`

- [ ] **Step 1: Write failing evidence and policy tests**

Create `test_evidence.py` with tests that use these exact factories and assertions:

```python
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
```

Create `test_privacy.py`:

```python
from datetime import UTC, datetime
from uuid import UUID

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
        evidence_ids=[EVIDENCE_ID],
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
    assert effective_export_permission(value, {EVIDENCE_ID: record}) is ExportPermission.REVIEW_REQUIRED


def test_restricted_evidence_prohibits_export() -> None:
    value = EvidenceBackedValue[str](value="Sensitive fact", evidence_ids=[EVIDENCE_ID])
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
    value = EvidenceBackedValue[str](value="Disputed fact", evidence_ids=[EVIDENCE_ID])
    record = EvidenceRecord(
        evidence_id=EVIDENCE_ID,
        kind=EvidenceKind.REFERENCE,
        statement="Disputed fact",
        verification_status=VerificationStatus.DISPUTED,
        export_permission=ExportPermission.ALLOWED,
        created_at=datetime(2026, 8, 24, 16, 0, tzinfo=UTC),
    )
    assert effective_export_permission(value, {EVIDENCE_ID: record}) is ExportPermission.PROHIBITED
```

- [ ] **Step 2: Run the focused tests and observe missing interfaces**

Run: `python -m pytest packages/core/tests/test_evidence.py packages/core/tests/test_privacy.py -v`

Expected: collection fails because `models.evidence` does not exist.

- [ ] **Step 3: Implement evidence types and policy helpers**

Create `evidence.py` with:

```python
from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Annotated, Generic, TypeVar
from uuid import UUID

from pydantic import Field, HttpUrl, field_validator, model_validator

from .common import (
    AwareDateTime,
    ContentOrigin,
    ContractModel,
    DateRange,
    ExportPermission,
    NonBlankStr,
    PrivacyClassification,
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
    evidence_id: UUID
    kind: EvidenceKind
    statement: NonBlankStr
    issuer: NonBlankStr | None = None
    source_url: HttpUrl | None = None
    applicable_dates: DateRange | None = None
    verification_status: VerificationStatus = VerificationStatus.SELF_ATTESTED
    privacy: PrivacyClassification = PrivacyClassification.PRIVATE
    export_permission: ExportPermission = ExportPermission.REVIEW_REQUIRED
    created_at: AwareDateTime
    verified_at: AwareDateTime | None = None

    @model_validator(mode="after")
    def validate_evidence_policy(self) -> "EvidenceRecord":
        if self.privacy is PrivacyClassification.RESTRICTED:
            if self.export_permission is not ExportPermission.PROHIBITED:
                raise ValueError("restricted evidence must prohibit export")
        if self.verification_status is VerificationStatus.SELF_ATTESTED and self.verified_at:
            raise ValueError("self-attested evidence cannot have a verification timestamp")
        if self.verification_status in {
            VerificationStatus.SOURCE_VERIFIED,
            VerificationStatus.THIRD_PARTY_VERIFIED,
        } and self.issuer is None and self.source_url is None:
            raise ValueError("verified evidence requires an issuer or source URL")
        return self


EvidenceValueT = TypeVar("EvidenceValueT")
PolicyValueT = TypeVar("PolicyValueT")


class EvidenceBackedValue(ContractModel, Generic[EvidenceValueT]):
    value: EvidenceValueT
    origin: ContentOrigin = ContentOrigin.USER
    evidence_ids: Annotated[list[UUID], Field(min_length=1)]
    privacy: PrivacyClassification = PrivacyClassification.PRIVATE
    export_permission: ExportPermission = ExportPermission.REVIEW_REQUIRED

    @field_validator("evidence_ids")
    @classmethod
    def unique_evidence_ids(cls, values: list[UUID]) -> list[UUID]:
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
    value: EvidenceBackedValue[PolicyValueT], evidence_by_id: Mapping[UUID, EvidenceRecord]
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
```

- [ ] **Step 4: Run evidence, privacy, lint, and type checks**

Run: `python -m pytest packages/core/tests/test_evidence.py packages/core/tests/test_privacy.py -v`

Expected: 8 tests pass.

Run: `python -m ruff check packages/core && python -m mypy packages/core/src`

Expected: both commands pass without suppressing type errors.

- [ ] **Step 5: Commit evidence and policy behavior**

```bash
git add packages/core/src/autonomous_career_engine/core/models packages/core/tests/test_evidence.py packages/core/tests/test_privacy.py
git commit -m "feat(core): add evidence and export policy"
```

---

### Task 3: Candidate profile aggregate

**Files:**
- Create: `packages/core/src/autonomous_career_engine/core/models/candidate.py`
- Create: `packages/core/tests/test_candidate.py`
- Modify: `packages/core/src/autonomous_career_engine/core/__init__.py`

**Interfaces:**
- Consumes: `ProfileValue[T]`, `EvidenceRecord`, `EvidenceBackedValue[T]`, `DateRange`, and shared policy enums
- Produces: `ContactInfo`, `WorkExperience`, `Education`, `Certification`, `Skill`, `Project`, `JobPreferences`, `GeneratedSummary`, and `CandidateProfile`

- [ ] **Step 1: Write failing aggregate-validation tests**

Create `test_candidate.py` around this minimal valid profile factory:

```python
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
```

- [ ] **Step 2: Run the candidate tests and verify the missing module failure**

Run: `python -m pytest packages/core/tests/test_candidate.py -v`

Expected: collection fails because `models.candidate` does not exist.

- [ ] **Step 3: Implement focused candidate sections and aggregate validation**

Create `candidate.py`. Use `ContractModel` for every class and these exact public fields:

```python
from collections.abc import Iterator
from typing import Annotated, Literal
from uuid import UUID

from pydantic import EmailStr, Field, model_validator

from .common import (
    AwareDateTime,
    ContentOrigin,
    ContractModel,
    DateRange,
    ExportPermission,
    NonBlankStr,
    PrivacyClassification,
    ProfileValue,
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
    highlights: list[EvidenceBackedValue[NonBlankStr]] = Field(default_factory=list)


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
    preferred_titles: ProfileValue[list[NonBlankStr]] | None = None
    preferred_locations: ProfileValue[list[NonBlankStr]] | None = None
    remote_preference: ProfileValue[NonBlankStr] | None = None
    minimum_compensation: ProfileValue[int] | None = None


class GeneratedSummary(ContractModel):
    text: NonBlankStr
    origin: Literal[ContentOrigin.AI_GENERATED] = ContentOrigin.AI_GENERATED
    evidence_ids: list[UUID] = Field(default_factory=list)
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
    if isinstance(value, list):
        for item in value:
            yield from _evidence_references(item)


class CandidateProfile(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    candidate_id: UUID
    contact: ContactInfo
    work_experience: list[WorkExperience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    preferences: JobPreferences | None = None
    generated_summaries: list[GeneratedSummary] = Field(default_factory=list)
    evidence: list[EvidenceRecord] = Field(default_factory=list)
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
```

Set `packages/core/src/autonomous_career_engine/core/__init__.py` to:

```python
from .models.candidate import CandidateProfile

__all__ = ("CandidateProfile",)
```

- [ ] **Step 4: Run candidate and regression tests**

Run: `python -m pytest packages/core/tests/test_candidate.py packages/core/tests/test_common.py packages/core/tests/test_evidence.py packages/core/tests/test_privacy.py -v`

Expected: all tests pass.

Run: `python -m ruff check packages/core && python -m mypy packages/core/src`

Expected: both commands pass. Keep any mypy-safe recursive traversal change private to `candidate.py`; do not weaken the public types.

- [ ] **Step 5: Commit the candidate aggregate**

```bash
git add packages/core/src/autonomous_career_engine/core packages/core/tests/test_candidate.py
git commit -m "feat(core): add candidate profile contract"
```

---

### Task 4: Canonical job and field-level provenance

**Files:**
- Create: `packages/core/src/autonomous_career_engine/core/models/job.py`
- Create: `packages/core/tests/test_job.py`
- Modify: `packages/core/src/autonomous_career_engine/core/__init__.py`

**Interfaces:**
- Consumes: `ContractModel`, `NonBlankStr`, `AwareDateTime`, `Confidence`, and `ContentOrigin`
- Produces: `SourceRecord`, `SourceReference`, `ProvenancedValue[T]`, `Compensation`, `CompensationPeriod`, `JobLocation`, `WorkplaceType`, `EmploymentType`, and `CanonicalJob`

- [ ] **Step 1: Write failing job-provenance and compensation tests**

Create `test_job.py`:

```python
from datetime import UTC, datetime
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
```

- [ ] **Step 2: Run the job tests and verify the missing module failure**

Run: `python -m pytest packages/core/tests/test_job.py -v`

Expected: collection fails because `models.job` does not exist.

- [ ] **Step 3: Implement source records, provenanced values, and canonical jobs**

Create `job.py` with the following public model shape and validators:

```python
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import Field, HttpUrl, StringConstraints, field_validator, model_validator

from .common import AwareDateTime, Confidence, ContentOrigin, ContractModel, NonBlankStr


class SourceRecord(ContractModel):
    source_id: UUID
    provider: NonBlankStr
    external_id: NonBlankStr | None = None
    source_url: HttpUrl | None = None
    observed_at: AwareDateTime
    terms_url: HttpUrl | None = None
    access_restrictions: list[NonBlankStr] = Field(default_factory=list)

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
    value: JobValueT
    sources: Annotated[list[SourceReference], Field(min_length=1)]
    origin: ContentOrigin = ContentOrigin.SOURCE
    confidence: Confidence | None = None

    @field_validator("sources")
    @classmethod
    def unique_source_references(cls, values: list[SourceReference]) -> list[SourceReference]:
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


class Compensation(ContractModel):
    minimum: Decimal | None = None
    maximum: Decimal | None = None
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
        if self.minimum is not None and self.maximum is not None:
            if self.maximum < self.minimum:
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


class CanonicalJob(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    job_id: UUID
    sources: Annotated[list[SourceRecord], Field(min_length=1)]
    employer: ProvenancedValue[NonBlankStr]
    title: ProvenancedValue[NonBlankStr]
    description: ProvenancedValue[NonBlankStr] | None = None
    responsibilities: ProvenancedValue[list[NonBlankStr]] | None = None
    locations: ProvenancedValue[list[JobLocation]] | None = None
    workplace_type: ProvenancedValue[WorkplaceType] | None = None
    employment_type: ProvenancedValue[EmploymentType] | None = None
    compensation: ProvenancedValue[Compensation] | None = None
    requirements: ProvenancedValue[list[NonBlankStr]] | None = None
    qualifications: ProvenancedValue[list[NonBlankStr]] | None = None
    eligibility_constraints: ProvenancedValue[list[NonBlankStr]] | None = None
    application_url: ProvenancedValue[HttpUrl] | None = None
    posted_at: ProvenancedValue[date] | None = None
    closing_at: ProvenancedValue[date] | None = None
    posting_observed_at: ProvenancedValue[AwareDateTime] | None = None

    @model_validator(mode="after")
    def validate_aggregate(self) -> "CanonicalJob":
        source_ids = [source.source_id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("duplicate source IDs")
        known = set(source_ids)
        referenced = {
            reference.source_id
            for field_name in type(self).model_fields
            if isinstance((field_value := getattr(self, field_name)), ProvenancedValue)
            for reference in field_value.sources
        }
        missing = sorted(referenced - known, key=str)
        if missing:
            raise ValueError(f"missing source references: {', '.join(map(str, missing))}")
        if self.posted_at and self.closing_at:
            if self.closing_at.value < self.posted_at.value:
                raise ValueError("closing date cannot precede posted date")
        return self
```

Replace `packages/core/src/autonomous_career_engine/core/__init__.py` with:

```python
from .models.candidate import CandidateProfile
from .models.job import CanonicalJob

__all__ = ("CandidateProfile", "CanonicalJob")
```

- [ ] **Step 4: Run job and full regression tests**

Run: `python -m pytest packages/core/tests -v`

Expected: all tests pass.

Run: `python -m ruff check packages/core && python -m mypy packages/core/src`

Expected: both commands pass. If Ruff flags the assignment expression in the aggregate comprehension, replace it with a private `_source_references()` iterator and test the same behavior; do not loosen provenance validation.

- [ ] **Step 5: Commit the canonical job contract**

```bash
git add packages/core/src/autonomous_career_engine/core packages/core/tests/test_job.py
git commit -m "feat(core): add canonical job provenance"
```

---

### Task 5: Deterministic JSON Schema and synthetic examples

**Files:**
- Create: `packages/core/src/autonomous_career_engine/core/schema.py`
- Create: `packages/core/tests/test_schema_generation.py`
- Create: `packages/core/tests/test_examples.py`
- Create: `packages/core/examples/v1/candidate-profile.valid.json`
- Create: `packages/core/examples/v1/canonical-job.valid.json`
- Create: `packages/core/examples/v1/invalid/candidate-profile.missing-evidence.json`
- Create: `packages/core/examples/v1/invalid/canonical-job.missing-provenance.json`
- Generate: `packages/core/schemas/v1/candidate-profile.schema.json`
- Generate: `packages/core/schemas/v1/canonical-job.schema.json`

**Interfaces:**
- Consumes: `CandidateProfile.model_json_schema()` and `CanonicalJob.model_json_schema()`
- Produces: `render_schemas() -> dict[str, str]`, `write_schemas(output_dir: Path) -> None`, `check_schemas(output_dir: Path) -> list[str]`, and `python -m autonomous_career_engine.core.schema [--check]`

- [ ] **Step 1: Write failing schema-registry and fixture tests**

Create `test_schema_generation.py`:

```python
from pathlib import Path

from autonomous_career_engine.core.schema import check_schemas, render_schemas

CORE_ROOT = Path(__file__).parents[1]


def test_public_schema_registry_is_stable() -> None:
    assert set(render_schemas()) == {
        "candidate-profile.schema.json",
        "canonical-job.schema.json",
    }


def test_checked_in_schemas_match_models() -> None:
    assert check_schemas(CORE_ROOT / "schemas" / "v1") == []
```

Create `test_examples.py`:

```python
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
def test_invalid_examples_fail(model: type[CandidateProfile] | type[CanonicalJob], filename: str) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(load(EXAMPLES / "invalid" / filename))
```

- [ ] **Step 2: Run the schema and example tests and observe missing artifacts**

Run: `python -m pytest packages/core/tests/test_schema_generation.py packages/core/tests/test_examples.py -v`

Expected: collection fails because `core.schema` does not exist; after that module is introduced, tests continue failing until examples and generated schemas exist.

- [ ] **Step 3: Implement deterministic schema rendering and checking**

Create `schema.py`:

```python
import argparse
import json
from pathlib import Path

from pydantic import BaseModel

from .models.candidate import CandidateProfile
from .models.job import CanonicalJob

PUBLIC_SCHEMAS: dict[str, tuple[type[BaseModel], str]] = {
    "candidate-profile.schema.json": (
        CandidateProfile,
        "https://github.com/lulobello/autonomous-career-engine/schemas/v1/candidate-profile.schema.json",
    ),
    "canonical-job.schema.json": (
        CanonicalJob,
        "https://github.com/lulobello/autonomous-career-engine/schemas/v1/canonical-job.schema.json",
    ),
}


def render_schemas() -> dict[str, str]:
    rendered: dict[str, str] = {}
    for filename, (model, schema_id) in PUBLIC_SCHEMAS.items():
        schema = model.model_json_schema(mode="serialization")
        schema["$id"] = schema_id
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        rendered[filename] = json.dumps(schema, indent=2, sort_keys=True) + "\n"
    return rendered


def write_schemas(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in render_schemas().items():
        (output_dir / filename).write_text(content, encoding="utf-8")


def check_schemas(output_dir: Path) -> list[str]:
    mismatches: list[str] = []
    for filename, expected in render_schemas().items():
        path = output_dir / filename
        if not path.exists() or path.read_text(encoding="utf-8") != expected:
            mismatches.append(filename)
    return mismatches


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate public core JSON Schemas")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parents[3] / "schemas" / "v1",
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        mismatches = check_schemas(args.output_dir)
        if mismatches:
            parser.error(f"schema artifacts are stale: {', '.join(mismatches)}")
        return 0
    write_schemas(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Add minimal valid and representative invalid JSON examples**

Create `candidate-profile.valid.json` with one private name, one self-attested skill, and matching evidence:

```json
{
  "schema_version": "1.0",
  "candidate_id": "00000000-0000-4000-8000-000000000001",
  "contact": {
    "full_name": {
      "value": "Avery Example",
      "origin": "user",
      "privacy": "private",
      "export_permission": "review_required"
    }
  },
  "skills": [{
    "skill_id": "20000000-0000-4000-8000-000000000001",
    "name": {
      "value": "Python",
      "origin": "user",
      "evidence_ids": ["10000000-0000-4000-8000-000000000001"],
      "privacy": "private",
      "export_permission": "review_required"
    }
  }],
  "evidence": [{
    "evidence_id": "10000000-0000-4000-8000-000000000001",
    "kind": "user_attestation",
    "statement": "Avery uses Python in fictional portfolio projects.",
    "verification_status": "self_attested",
    "privacy": "private",
    "export_permission": "review_required",
    "created_at": "2026-08-24T16:00:00Z"
  }],
  "created_at": "2026-08-24T16:00:00Z",
  "updated_at": "2026-08-24T16:00:00Z"
}
```

Create `canonical-job.valid.json` with one source and two provenanced required fields:

```json
{
  "schema_version": "1.0",
  "job_id": "30000000-0000-4000-8000-000000000001",
  "sources": [{
    "source_id": "40000000-0000-4000-8000-000000000001",
    "provider": "synthetic_import",
    "external_id": "example-job-001",
    "source_url": "https://jobs.example.com/example-job-001",
    "observed_at": "2026-08-24T16:00:00Z"
  }],
  "employer": {
    "value": "Example Analytics Cooperative",
    "sources": [{
      "source_id": "40000000-0000-4000-8000-000000000001",
      "source_field": "employer"
    }],
    "origin": "source"
  },
  "title": {
    "value": "Data Engineer",
    "sources": [{
      "source_id": "40000000-0000-4000-8000-000000000001",
      "source_field": "title"
    }],
    "origin": "source"
  }
}
```

Create `invalid/candidate-profile.missing-evidence.json` with a skill reference that cannot resolve:

```json
{
  "schema_version": "1.0",
  "candidate_id": "00000000-0000-4000-8000-000000000002",
  "contact": {
    "full_name": {
      "value": "Jordan Example",
      "origin": "user",
      "privacy": "private",
      "export_permission": "review_required"
    }
  },
  "skills": [{
    "skill_id": "20000000-0000-4000-8000-000000000002",
    "name": {
      "value": "SQL",
      "origin": "user",
      "evidence_ids": ["10000000-0000-4000-8000-000000000099"],
      "privacy": "private",
      "export_permission": "review_required"
    }
  }],
  "evidence": [],
  "created_at": "2026-08-24T16:00:00Z",
  "updated_at": "2026-08-24T16:00:00Z"
}
```

Create `invalid/canonical-job.missing-provenance.json` with an empty provenance list on the title:

```json
{
  "schema_version": "1.0",
  "job_id": "30000000-0000-4000-8000-000000000002",
  "sources": [{
    "source_id": "40000000-0000-4000-8000-000000000002",
    "provider": "synthetic_import",
    "external_id": "example-job-002",
    "source_url": "https://jobs.example.com/example-job-002",
    "observed_at": "2026-08-24T16:00:00Z"
  }],
  "employer": {
    "value": "Example Systems Studio",
    "sources": [{
      "source_id": "40000000-0000-4000-8000-000000000002",
      "source_field": "employer"
    }],
    "origin": "source"
  },
  "title": {
    "value": "Platform Engineer",
    "sources": [],
    "origin": "source"
  }
}
```

Both files are intentional negative examples and contain no personal data.

- [ ] **Step 5: Generate the committed schemas and run focused tests**

Run: `python -m autonomous_career_engine.core.schema --output-dir packages/core/schemas/v1`

Expected: both schema files are created with a trailing newline.

Run: `python -m pytest packages/core/tests/test_schema_generation.py packages/core/tests/test_examples.py -v`

Expected: all schema and example tests pass.

- [ ] **Step 6: Verify deterministic regeneration and the complete test suite**

Run: `python -m autonomous_career_engine.core.schema --check --output-dir packages/core/schemas/v1`

Expected: exit status 0 with no stale-artifact error.

Run: `python -m pytest packages/core/tests -v`

Expected: all tests pass.

Run: `python -m ruff check packages/core && python -m mypy packages/core/src`

Expected: both commands pass.

- [ ] **Step 7: Commit schemas and examples**

```bash
git add packages/core/src/autonomous_career_engine/core/schema.py packages/core/tests packages/core/examples packages/core/schemas
git commit -m "feat(core): publish versioned JSON schemas"
```

---

### Task 6: Contributor documentation and continuous verification

**Files:**
- Create: `.github/workflows/core-ci.yml`
- Modify: `packages/core/README.md`
- Modify: `README.md`
- Modify: `CONTRIBUTING.md`

**Interfaces:**
- Consumes: package installation, pytest suite, Ruff, mypy, and schema `--check` command from Tasks 1–5
- Produces: reproducible contributor instructions and a public CI gate for Issue #1 contracts

- [ ] **Step 1: Add the CI workflow as a reproducible repository check**

Create `.github/workflows/core-ci.yml`:

```yaml
name: Core contracts

on:
  pull_request:
    paths:
      - "packages/core/**"
      - ".github/workflows/core-ci.yml"
  push:
    branches: [main]
    paths:
      - "packages/core/**"
      - ".github/workflows/core-ci.yml"

permissions:
  contents: read

jobs:
  verify:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
          cache-dependency-path: packages/core/pyproject.toml
      - name: Install core package
        run: python -m pip install -e './packages/core[dev]'
      - name: Lint
        run: python -m ruff check packages/core
      - name: Type check
        run: python -m mypy packages/core/src
      - name: Test
        run: python -m pytest packages/core/tests -v
      - name: Check generated schemas
        run: python -m autonomous_career_engine.core.schema --check --output-dir packages/core/schemas/v1
```

Before documentation changes, run all four CI commands locally from the repository root. Any failure blocks documentation/status updates because the capability is not yet demonstrably available.

- [ ] **Step 2: Replace the placeholder core README with exact contributor guidance**

Document these commands in `packages/core/README.md`:

```bash
python -m pip install -e './packages/core[dev]'
python -m pytest packages/core/tests -v
python -m ruff check packages/core
python -m mypy packages/core/src
python -m autonomous_career_engine.core.schema --check --output-dir packages/core/schemas/v1
```

Also document:

- stable imports `from autonomous_career_engine.core import CandidateProfile, CanonicalJob`;
- Python models are authoritative and `schemas/v1` is generated;
- how to regenerate schemas without `--check`;
- privacy defaults and the most-restrictive effective export rule;
- every candidate career fact requires evidence and every job field requires provenance;
- v1 compatible versus breaking changes exactly as defined in the spec;
- examples are synthetic and real candidate data is prohibited in commits.

- [ ] **Step 3: Make root status and contribution instructions accurate**

In `README.md`, add this tested capability row directly after architecture and safety:

```markdown
| Canonical candidate and job contracts | Available | Versioned, provenance-aware Pydantic models and generated JSON Schema |
```

Change the foundation-stage sentence to state that governance, architecture, and the first executable contracts are published, while discovery, ranking, documents, applications, and tracking remain unimplemented.

In `CONTRIBUTING.md`, replace the sentence that says language-specific commands will be added later with a link to `packages/core/README.md`, while clarifying that other packages remain documentation-only. Add schema changes to the architecture-decision rule and require contributors to regenerate schemas and preserve v1 fixtures.

- [ ] **Step 4: Run the clean-install and full verification sequence**

Create a fresh virtual environment outside the repository:

```bash
ace_verify_dir=$(mktemp -d)
python3.12 -m venv "$ace_verify_dir"
"$ace_verify_dir/bin/python" -m pip install -e './packages/core[dev]'
"$ace_verify_dir/bin/python" -m ruff check packages/core
"$ace_verify_dir/bin/python" -m mypy packages/core/src
"$ace_verify_dir/bin/python" -m pytest packages/core/tests -v
"$ace_verify_dir/bin/python" -m autonomous_career_engine.core.schema --check --output-dir packages/core/schemas/v1
```

Expected: installation succeeds and all four verification commands exit 0. Do not mark the capability Available if any command fails.

- [ ] **Step 5: Inspect the public diff for privacy and upstream provenance**

Run: `git grep -n -E '(BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|api[_-]?key|access[_-]?token|password)' -- packages/core README.md CONTRIBUTING.md`

Expected: no matches.

Run: `git diff --check`

Expected: no whitespace errors.

Run: `git diff --stat`

Expected: only Issue #1 core contracts, generated schemas, synthetic examples, CI, and related documentation are present.

- [ ] **Step 6: Commit the contributor and CI integration**

```bash
git add .github/workflows/core-ci.yml packages/core/README.md README.md CONTRIBUTING.md
git commit -m "ci: verify canonical core contracts"
```

- [ ] **Step 7: Record final Issue #1 evidence**

Run:

```bash
git status --short
git log --oneline --decorate -7
python -m pytest packages/core/tests -q
python -m autonomous_career_engine.core.schema --check --output-dir packages/core/schemas/v1
```

Expected: the worktree is clean, the plan's implementation commits are visible, all tests pass, and schema check exits 0. Capture the exact test count and command results in the pull-request description; link Issue #1 and do not claim discovery, ranking, generation, or application automation is implemented.
