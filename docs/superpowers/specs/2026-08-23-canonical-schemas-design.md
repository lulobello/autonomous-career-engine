# Canonical Candidate and Job Schemas

**Status:** Approved for Issue #1 implementation

**Approved:** 2026-08-24

**Schema version:** `1.0`

**Repository milestone:** Foundation — v0.1

## Purpose

Issue #1 establishes the first executable public contracts for Autonomous Career Engine: a canonical candidate profile, evidence records, and a canonical job. These contracts must let later packages rank jobs and draft application materials without losing provenance, confusing generated text with verified facts, or leaking private candidate information.

This design covers models, generated JSON Schema, synthetic examples, validation, privacy/export rules, compatibility, and contract tests. It deliberately excludes persistence, provider-specific job payloads, ranking, document generation, ATS automation, and real candidate data.

## Design goals

1. Make factual candidate claims traceable to evidence.
2. Make every present normalized job field traceable to one or more sources.
3. Distinguish source facts, user input, derived values, and AI-generated content.
4. Make privacy and export decisions machine-enforceable.
5. Offer both ergonomic Python types and language-neutral JSON Schema.
6. Reject ambiguous or malformed records with field-specific errors.
7. Evolve the public contract without silently breaking stored records or contributors.

## Selected approach

The authoritative contracts will be typed Pydantic v2 models in `packages/core`. Pydantic will perform runtime validation and generate JSON Schema from those same model definitions. Deterministically generated JSON Schema files will be committed so integrations in other languages do not need to execute Python.

The package targets Python 3.12 or newer and remains independent of databases, web frameworks, job providers, model providers, and user interfaces. All contract models reject unknown fields. Top-level aggregates carry an explicit schema version.

Pydantic is used as a normal third-party dependency; no Pydantic or other upstream source code, schemas, fixtures, prompts, or documentation will be copied into this repository. Dependency metadata and license compatibility will be recorded when the executable package is introduced, consistent with `docs/upstream-evaluation.md`.

## Package and artifact layout

```text
packages/core/
├── pyproject.toml
├── src/autonomous_career_engine/core/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── common.py
│   │   ├── evidence.py
│   │   ├── candidate.py
│   │   └── job.py
│   └── schema.py
├── schemas/v1/
│   ├── candidate-profile.schema.json
│   └── canonical-job.schema.json
├── examples/v1/
│   ├── candidate-profile.valid.json
│   ├── canonical-job.valid.json
│   └── invalid/
│       ├── candidate-profile.missing-evidence.json
│       └── canonical-job.missing-provenance.json
└── tests/
    ├── test_candidate.py
    ├── test_job.py
    ├── test_privacy.py
    └── test_schema_generation.py
```

`common.py` owns shared enums, identifiers, timestamps, privacy/export policy, content origin, and generic referenced-value types. `evidence.py` owns candidate evidence and verification concepts. `candidate.py` and `job.py` own their respective aggregates. `schema.py` provides the only supported schema-generation registry and deterministic export command.

## Shared model rules

All contract models use a common strict base configuration with unknown fields forbidden. Validation may parse documented JSON representations such as ISO 8601 dates, but must not perform surprising semantic coercion such as interpreting arbitrary text as a Boolean.

Shared primitives include:

- UUID identifiers serialized as strings;
- timezone-aware ISO 8601 timestamps;
- nonblank, whitespace-normalized strings;
- HTTP(S) source URLs;
- confidence values constrained to the inclusive range `0` through `1`;
- date ranges whose end cannot precede their start;
- schema version `Literal["1.0"]` on each top-level aggregate.

The record's aggregate identifier and schema version are control metadata and do not require field provenance. Every present normalized job-domain value does.

## Provenance model

### Source record

A `SourceRecord` identifies one observed job source without embedding its raw provider payload. It contains:

- a stable internal `source_id`;
- a provider or source type, such as a user import or an approved adapter;
- the provider's external identifier when available;
- a canonical HTTP(S) source URL when available;
- `observed_at`, always timezone-aware;
- optional source-level access-policy metadata needed by later adapters.

At least one of external identifier or source URL must be present. Provider-specific fields remain outside `packages/core` and are translated at adapter boundaries.

### Source reference

A `SourceReference` points from a normalized field to a `SourceRecord`. It contains `source_id`, the original source-field path when known, and optional observation metadata. It does not copy long source text into the canonical record.

### Provenanced value

A generic `ProvenancedValue[T]` wraps a normalized value with:

- `value: T`;
- one or more `SourceReference` entries;
- `origin`, classified as `source`, `user`, `derived`, or `ai_generated`;
- optional confidence for a derived value.

Each present normalized field on `CanonicalJob` uses this wrapper. Unknown optional information is represented by absence, not a guessed value with artificial confidence.

Aggregate validation ensures every source reference resolves to a source record contained in the same canonical job. This gives consumers a local, serializable proof trail without binding them to a discovery provider.

## Candidate evidence model

### Evidence record

An `EvidenceRecord` represents support for candidate facts. It contains:

- a stable `evidence_id`;
- an evidence kind such as user attestation, employment record, education record, certification, portfolio artifact, or reference;
- a concise factual statement or explicitly typed structured fact;
- source/issuer information appropriate to that kind;
- applicable dates;
- verification status;
- privacy classification;
- export permission;
- creation and optional verification timestamps.

Verification status is one of:

- `self_attested`;
- `source_verified`;
- `third_party_verified`;
- `disputed`.

The schema records a verification status; it does not itself perform verification. AI-generated content is not eligible to become an `EvidenceRecord`, so it cannot acquire evidence verification through labeling. A disputed record cannot authorize an application claim.

### Evidence-backed candidate values

Factual candidate fields use an `EvidenceBackedValue[T]` wrapper containing:

- `value: T`;
- `origin`;
- one or more evidence identifiers;
- privacy classification;
- export permission.

A user assertion about experience, education, a certification, a skill, or a project is represented by an evidence record whose kind is user attestation and whose status is `self_attested`. This keeps every career fact traceable without presenting self-attestation as independent verification. Contact details and job preferences use a separate `ProfileValue[T]` wrapper with origin, privacy, and export policy but do not require documentary evidence.

Generated summaries are stored separately from factual profile sections. They may reference the evidence used to generate them, but their origin remains `ai_generated` and they cannot become verified evidence automatically.

## Candidate profile

`CandidateProfile` is the versioned aggregate and contains:

- `candidate_id` and `schema_version`;
- private contact information;
- work experience;
- education;
- certifications;
- skills;
- projects or portfolio items;
- job preferences and constraints;
- optional generated summaries;
- the evidence-record collection referenced by its factual values;
- created and updated timestamps.

The first version models only fields needed for near-term discovery, ranking, and truthful document generation. Demographic or legally sensitive attributes are not added speculatively. Future additions require an explicit use case, privacy analysis, and compatibility review.

Cross-record validation rejects missing evidence references, duplicate evidence identifiers, and generated summaries presented as source facts. A policy helper reports the admissible verification state of a factual value from its referenced evidence; it never upgrades `self_attested` or `disputed` evidence to a verified state.

## Canonical job

`CanonicalJob` is the versioned aggregate and contains:

- `job_id` and `schema_version`;
- one or more `SourceRecord` entries;
- provenanced employer and title;
- optional provenanced description and responsibilities;
- optional provenanced locations and workplace type;
- optional provenanced employment type;
- optional provenanced compensation;
- optional provenanced requirements and qualifications;
- optional provenanced eligibility or authorization constraints;
- optional provenanced application URL;
- optional provenanced posted, closing, and observed dates.

Compensation uses a structured value with optional minimum and maximum, ISO currency, and a period such as hour, month, or year. If both bounds are present, the maximum cannot be below the minimum. A range cannot mix currencies or periods.

Locations are structured rather than flattened into one display string. Workplace and employment classifications use documented enums with an explicit `unknown` or `other` value only where the source genuinely cannot map to a stable classification. Free-text source values remain in discovery-layer provenance, not improvised enum members.

Duplicate postings are a discovery concern. A later deduplication process may combine source records into one canonical job, but this schema already supports that result by allowing multiple sources and multiple references per field.

## Privacy and export policy

Privacy classification is one of:

- `public`: safe for intentional public display;
- `internal`: usable within the local workflow but not normally published;
- `private`: personal information exposed only to a requested application destination;
- `restricted`: never exported by automated document or application workflows.

Export permission is one of:

- `allowed`;
- `review_required`;
- `prohibited`.

Privacy and export permission are intentionally separate. The effective export decision is the most restrictive combination of the candidate value and all evidence it references. `restricted` always implies `prohibited`. `ai_generated` content defaults to `review_required`. Contact information defaults to `private`; it is not public merely because a particular application may use it.

Issue #1 defines and tests this policy calculation in `packages/core`. It does not yet implement a resume or ATS exporter.

## Validation and failure behavior

Validation fails closed and reports precise field locations. Important cross-field rules include:

- all referenced source and evidence identifiers resolve within their aggregate;
- duplicate identifiers within an aggregate are rejected;
- all present canonical job fields include a nonempty provenance list;
- timestamps that represent observations are timezone-aware;
- chronological ranges are ordered;
- compensation bounds, currency, and period are coherent;
- prohibited or restricted values cannot claim export is allowed;
- generated content cannot be inserted into the evidence collection;
- evidence policy helpers cannot report missing, disputed, or self-attested evidence as source- or third-party-verified;
- application and source URLs use HTTP(S);
- unknown properties are rejected throughout nested models.

Missing source information remains absent. No validator fabricates employers, dates, compensation, requirements, evidence, confidence, or verification.

## JSON Schema generation

The Python models are authoritative. `schema.py` maintains an explicit registry of top-level public schemas and exports them through Pydantic's JSON Schema API.

Generation is deterministic: JSON uses stable key ordering, two-space indentation, and one trailing newline. The checked-in files live under a major-version directory and carry stable schema identifiers. A test regenerates schemas in memory and compares exact bytes with the committed artifacts. Contributors who alter a model must intentionally regenerate and review the corresponding schema diff.

Internal helper models may appear in generated `$defs`, but only the candidate profile and canonical job are advertised as top-level public contracts in v1.

## Versioning and compatibility

The schema version is independent of the repository release version. Initial aggregates use `1.0` while the project is in Foundation v0.1.

Within a major version, compatible changes may add optional fields or relax validation without changing existing meaning. Removing or renaming a field, changing its meaning or type, making an optional field required, tightening accepted values, or changing privacy/export semantics requires a new major schema directory and migration guidance.

Published major-version schema files are never rewritten incompatibly. A compatibility test will preserve representative v1 fixtures as the models evolve. Changes to a public schema require documentation and review as an architecture decision under the contribution rules.

## Synthetic fixtures and tests

All examples use obviously fictional people, employers, reserved example domains, identifiers, and evidence. No fixture may contain a real resume, contact detail, credential, access token, or application answer. Named invalid example files document their expected failure and focused tests exercise additional invalid cases without creating a large fixture-maintenance burden.

The test suite covers:

1. valid candidate and job fixtures validate, serialize, and round-trip;
2. unknown fields are rejected at top-level and nested locations;
3. blank strings, invalid URLs, naive timestamps, and reversed dates fail clearly;
4. missing or duplicate evidence/source references fail;
5. every present normalized job field carries resolvable provenance;
6. generated summaries cannot masquerade as verified evidence;
7. disputed or self-attested-only evidence cannot be reported as a verified claim;
8. privacy and export combinations resolve to the most restrictive result;
9. invalid compensation ranges fail;
10. generated JSON Schema matches the committed files byte for byte;
11. valid v1 examples remain valid after compatible changes.

## Acceptance-criteria mapping

| Issue #1 acceptance criterion | Design response |
| --- | --- |
| Distinguish verified evidence from generated summaries | Separate evidence records and generated summaries; origin and verification invariants prevent promotion by labeling. |
| Every normalized job field references its source | `ProvenancedValue[T]` is mandatory for every present job-domain field, with aggregate reference validation. |
| Document private fields and export behavior | Explicit privacy/export enums, conservative defaults, and most-restrictive policy calculation. |
| Provide synthetic valid and invalid examples | Committed valid and representative invalid examples plus focused invalid constructions in tests, all fictional. |
| Define versioning and compatibility rules | Top-level `1.0`, stable `schemas/v1`, compatibility definitions, drift and fixture tests. |

## Alternatives considered

### Hand-written JSON Schema as the authority

This is language-neutral but duplicates validation logic in Python and creates two sources of truth. It was rejected because contract drift is likely during early development.

### Standard-library dataclasses plus custom validation

This minimizes dependencies but requires substantial bespoke validation, error reporting, serialization, and schema-generation work. It was rejected because that work does not differentiate the project and would make the first public contract less reliable.

### Flat fields with aggregate-level provenance notes

This is easier to read but cannot prove which source supports a particular normalized value, especially when several postings are merged. It was rejected because it fails a central acceptance criterion.

### One generic document model

This is flexible but weakens type safety, contributor guidance, privacy enforcement, and compatibility guarantees. It was rejected in favor of focused domain models and small reusable wrappers.

## Consequences and limits

The field wrappers make serialized records more verbose, but the verbosity is intentional: downstream decisions can inspect value, origin, evidence, and exportability without hidden side channels. The model is suitable for a public portfolio because it demonstrates explicit domain boundaries, data lineage, safety policy, and contract testing.

This design does not claim that a candidate fact has been independently verified merely because a status field says so. Verification processes, storage, provider adapters, ranking, documents, and applications remain later issues. Implementations must continue to treat external content and generated model output as untrusted.

## Definition of done

Issue #1 is complete when the package installs in a clean supported Python environment; the public models and policy helpers are documented; valid examples and all tests pass; generated schema artifacts are current; contributor instructions include regeneration and compatibility steps; public status claims remain accurate; and the work is merged without copied upstream code or real personal data.
