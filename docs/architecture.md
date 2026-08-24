# Architecture

## Context

Autonomous Career Engine coordinates sensitive, stateful work across job sources, language models, document renderers, and application systems. Its architecture must make the safe path the easy path: verified evidence flows forward, external output is validated, submissions are review-first, and every meaningful transition is auditable.

The foundation uses a modular monorepo rather than distributed services. This keeps the first vertical slice simple while preserving boundaries that can later be deployed independently if scale or security requires it.

## System context

```text
                         External systems
             ┌────────────────────────────────┐
             │ Job sources  Model providers   │
             │ Document tools  ATS platforms  │
             └───────────┬────────────────────┘
                         │ adapter contracts
┌───────────────┐        ▼                         ┌──────────────┐
│ Job seeker    │ ◀── Autonomous Career Engine ─▶ │ Local store  │
│ review/control│        │                         │ and audit log│
└───────────────┘        ▼                         └──────────────┘
                  Exported application materials
```

## Package boundaries

### `packages/core`

Owns candidate profiles, evidence references, canonical jobs, application states, workflow policies, and orchestration interfaces. It must not depend on a specific job source, model provider, renderer, ATS, or database.

### `packages/discovery`

Owns source adapters, ingestion, normalization, provenance, and deduplication. Every normalized field retains enough source information to explain where it came from. Adapters expose terms, rate-limit, retry, and authentication requirements.

### `packages/ranking`

Owns hard filters, scoring factors, evidence, uncertainty, explanations, and configurable thresholds. It consumes canonical jobs and candidate preferences; it does not fetch jobs or submit applications.

### `packages/documents`

Owns evidence selection, prompt/model orchestration, structured draft output, claim validation, and rendering contracts. It treats model responses as untrusted and refuses or flags unsupported factual claims.

### `packages/applications`

Owns the application state machine, review gates, ATS adapter contracts, field preparation, idempotency, and submission receipts. A provider-specific adapter cannot bypass domain workflow policy.

### `packages/tracking`

Owns immutable application events, derived status views, outcome definitions, exports, and evaluation inputs. Learning uses recorded outcomes but does not silently mutate ranking policy.

### `packages/shared`

Owns narrowly shared primitives such as identifiers, timestamps, result types, configuration contracts, and redaction helpers. It must not become a miscellaneous dependency bucket.

### `apps/api` and `apps/web`

Entry points compose packages and present workflows. They contain transport and presentation concerns, not domain rules.

## Core data contracts

The first milestone will specify exact schemas. All implementations must preserve these semantic requirements:

- **Candidate profile:** preferences and verified experience separated from generated summaries.
- **Evidence record:** source, text or structured fact, verification state, and permitted uses.
- **Canonical job:** source identifier, source URL, observed time, normalized fields, raw-field provenance, and access policy metadata.
- **Fit assessment:** hard-filter decisions, weighted factor results, evidence, uncertainty, explanation, and scoring-policy version.
- **Application:** job and candidate references, workflow state, selected materials, review decision, submission policy, and timestamps.
- **Application event:** immutable transition, actor, reason, correlation/idempotency key, and redacted metadata.
- **Outcome:** explicit event type, observed time, source, and optional user notes stored privately.

## Data flow and trust boundaries

1. Candidate data enters through a local import or interface and is separated into verified evidence, preferences, and private metadata.
2. A discovery adapter ingests an opening and stores raw-source provenance before normalization.
3. Hard filters produce explicit pass/fail reasons. Ranking evaluates only eligible jobs and returns evidence-backed factors.
4. Shortlisting triggers document drafting. The document package can select only evidence permitted for the requested material.
5. Model output is parsed into a schema and each factual claim is checked against selected evidence.
6. A human reviews the job, materials, answers, and intended action.
7. The application package creates a prepared action with an idempotency key. An ATS adapter may execute it only when workflow policy permits.
8. Tracking appends events and derives the current view. Outcomes later feed an offline evaluation.
9. Learning produces a proposed configuration change with supporting evidence; the user chooses whether to apply it.

Job descriptions, uploaded documents, web pages, and model responses cross an untrusted-content boundary. They cannot alter workflow policy, retrieve unrelated secrets, or authorize submission.

## Application state model

```text
discovered → shortlisted → drafting → ready-for-review
                                      │
                      ┌───────────────┴───────────────┐
                      ▼                               ▼
                  approved                        rejected
                      │
                      ▼
                  submitting ─────failure────▶ ready-for-review
                      │
                      ▼
                  submitted → interviewing → offer / closed
```

Transitions are explicit and append an event. Withdrawal and archival are allowed from applicable nonterminal states. A retry reuses or safely supersedes the prior idempotency key and cannot create a second submission without a new approval.

## Automation modes

- **`watch`:** discover, normalize, and rank without drafting or applying.
- **`review`:** draft and prepare actions, then require explicit approval. This is the default.
- **`bounded-auto`:** a future opt-in mode limited by user-defined sources, roles, thresholds, time windows, and application counts. It must be disabled until its dedicated safety criteria are implemented and tested.

## Persistence and privacy

The storage technology will be decided in the first milestone. Regardless of technology:

- personal data and credentials are local by default;
- public fixtures are synthetic;
- secrets use environment or platform secret storage, never the database or logs;
- exports are explicit and redact internal metadata where appropriate;
- deletion and retention semantics are testable;
- schema migrations are versioned and reversible where practical;
- telemetry is opt-in and excludes application content.

## Failure handling

- External calls use timeouts, bounded retries with backoff, and rate-limit awareness.
- Validation failures return actionable, field-specific errors and preserve the draft.
- Partial workflows persist the last safe state and can resume.
- Submission attempts store a redacted receipt or failure reason.
- Correlation identifiers connect events without exposing private content.
- A circuit breaker or manual disable control can suspend a malfunctioning adapter.
- Unsupported or changed external forms fail closed before submission.

## Testing architecture

- **Unit:** schemas, policies, score factors, evidence selection, claim validation, and state transitions.
- **Contract:** each adapter against synthetic fixtures and deterministic provider doubles.
- **Integration:** discovery through `ready-for-review`, including failure and resume paths.
- **End to end:** a synthetic candidate and job; no live submission in default automation.
- **Security:** secret scanning, redaction, malicious job content, authorization gates, and duplicate-submission resistance.
- **Documentation:** relative links, capability-status accuracy, and runnable command checks.

## Evolution rules

1. Domain packages communicate through documented interfaces.
2. Provider-specific data is translated at adapter boundaries.
3. New integrations require an upstream and compliance evaluation.
4. New automation cannot weaken review, audit, or idempotency guarantees.
5. Splitting a package into a service requires a measured operational or security need, not anticipation alone.
