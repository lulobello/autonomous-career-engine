# Core package

This package publishes the versioned canonical contracts for candidate profiles and
jobs. It owns evidence references and export-policy helpers, and remains independent
of providers, databases, renderers, and user-interface frameworks.

## Install and verify

From the repository root, install the package and run its complete contract gate:

```bash
python -m pip install -e './packages/core[dev]'
python -m pytest packages/core/tests -v
python -m ruff check packages/core
python -m mypy packages/core/src
python -m autonomous_career_engine.core.schema --check --output-dir packages/core/schemas/v1
```

The stable top-level imports are:

```python
from autonomous_career_engine.core import CandidateProfile, CanonicalJob
```

## Schemas and compatibility

The Python Pydantic models are authoritative. Contract instances are immutable
snapshots; construct a new validated instance rather than mutating an existing one.
Collection inputs use JSON arrays and are stored as immutable tuples in Python.

The committed JSON Schema files in `schemas/v1` are generated structural contracts
for language-neutral consumers; do not edit them by hand. They enforce shapes,
required values, formats, reference-array cardinality and uniqueness where required,
and local policy, verification, source-identity, and confidence conditionals. Consumers
should enable Draft 2020-12 format validation. After changing a public model,
regenerate and review the schemas from the repository root:

```bash
python -m autonomous_career_engine.core.schema --output-dir packages/core/schemas/v1
```

Within a major schema version, compatible changes may add optional fields or relax
validation without changing existing meaning. Removing or renaming a field, changing
its meaning or type, making an optional field required, tightening accepted values,
or changing privacy/export semantics requires a new major schema directory and
migration guidance. Published major-version schema files are never rewritten
incompatibly; preserve the representative v1 fixtures when the models evolve.

### Semantic validation

JSON Schema cannot compare arbitrary values or resolve identifiers elsewhere in a
record. A language-neutral semantic validator must enforce these additional rules:

- candidate evidence IDs and job source IDs are unique within their aggregates;
- every factual or generated-summary evidence reference resolves to evidence in the
  same candidate profile;
- every normalized job source reference resolves to a source in the same canonical job;
- candidate `updated_at` is not earlier than `created_at`;
- date-range ends, job closing dates, and compensation maxima are not earlier or lower
  than their corresponding starts, posted dates, or minima;
- verification resolution rejects an empty reference set, fails on missing evidence,
  and never upgrades disputed or solely self-attested evidence; and
- effective export permission uses the most restrictive value and referenced-evidence
  policy, with restricted or disputed evidence always prohibiting export.

The Pydantic aggregate models and policy helpers implement these semantic rules for
Python consumers. Structural validation alone does not prove that a referenced record
exists or that a declared verification status is truthful.

## Privacy, evidence, and examples

Candidate values default to private and export review. The effective export decision
is the most restrictive combination of a candidate value and every evidence record
it references: restricted data, disputed evidence, or any prohibited permission
prohibits export. AI-generated content requires review and cannot become factual
evidence merely by labeling it.

Every candidate career fact must reference evidence. Every present normalized job
field must carry one or more source references. These contracts preserve provenance;
they do not implement verification, discovery, ranking, document generation, or
application automation.

Examples and fixtures are deliberately synthetic. Never commit real candidate data,
including resumes, contact details, credentials, application answers, or other
personal career records.
