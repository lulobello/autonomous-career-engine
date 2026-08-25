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

Owns immutable non-sensitive application-event envelopes, separately erasable sensitive details, derived status views, outcome definitions, exports, and evaluation inputs. Learning uses recorded outcomes but does not silently mutate ranking policy.

### `packages/shared`

Owns narrowly shared primitives such as identifiers, timestamps, result types, configuration contracts, and redaction helpers. It must not become a miscellaneous dependency bucket.

### `packages/persistence`

Owns repository interfaces, the local SQLite adapter, units of work, migrations, backup and restore, retention and deletion, storage health, and credential references. It depends on domain contracts but domain packages never depend on SQLite or a persistence framework. Live secret values remain in a platform credential vault and never enter persistence records.

### `apps/api` and `apps/web`

Entry points compose packages and present workflows. They contain transport and presentation concerns, not domain rules.

## Core data contracts

The first milestone will specify exact schemas. All implementations must preserve these semantic requirements:

- **Candidate profile:** preferences and verified experience separated from generated summaries.
- **Evidence record:** source, text or structured fact, verification state, and permitted uses.
- **Canonical job:** source identifier, source URL, observed time, normalized fields, raw-field provenance, and access policy metadata.
- **Fit assessment:** hard-filter decisions, weighted factor results, evidence, uncertainty, explanation, and scoring-policy version.
- **Application:** job and candidate references, workflow state, selected materials, review decision, submission policy, and timestamps.
- **Application event:** immutable non-sensitive envelope with opaque actor, policy version, decision, correlation/idempotency key, timestamp, and redacted control fields; optional sensitive description is a separately erasable linked detail.
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

External-action claims persist `claimed`, `in_flight`, `succeeded`, `failed`, or `indeterminate`. If a provider may have accepted a submission but no receipt was durably stored, the claim becomes `indeterminate`; automatic replay is blocked until provider reconciliation or explicit human resolution.

## Automation modes

- **`watch`:** discover, normalize, and rank without drafting or applying.
- **`review`:** draft and prepare actions, then require explicit approval. This is the default.
- **`bounded-auto`:** a future opt-in mode limited by user-defined sources, roles, thresholds, time windows, and application counts. It must be disabled until its dedicated safety criteria are implemented and tested.

## Persistence and privacy

The accepted [local persistence decision](decisions/0001-local-persistence.md) uses one SQLite database per local workspace behind replaceable repository interfaces. `packages/core` remains database-independent. The database and managed backups live in the operating system's private per-user application-data directory, outside the repository and automatically synchronized folders.

Validated domain aggregates are stored as versioned canonical JSON snapshots with relational control metadata and indexes. Each audit event uses an immutable non-sensitive envelope; optional personal or descriptive content is stored in a separately erasable linked detail. Before an external action, workflow state, the durable idempotency claim, approved policy version and decision, and redacted audit envelope commit atomically. The provider receipt and terminal claim state commit after the external response because that side effect cannot share a SQLite transaction. One engine process may write a database at a time.

Migrations are immutable ordered units with checksums and an application ledger. Pending migrations require a verified pre-migration backup and complete before autonomous workers start. A failed or unsupported migration blocks writes and recovers from a compatible backup rather than running improvised downgrade logic. A nontransactional migration stages a validated replacement on the active database's filesystem. The engine quiesces workers, closes connections, checkpoints or safely disposes WAL state, durably writes and atomically replaces the file, removes stale `-wal` and `-shm` sidecars after old connections close, and durably records parent-directory changes where supported. Ambiguous recovery state fails closed.

The engine creates at most one scheduled managed backup per 24 hours, always backs up before migration, and retains the newest seven. Portable backups are authenticated and password-encrypted, include version and integrity metadata, and exclude credentials. Restore validates a same-filesystem temporary copy and uses the same quiesced, WAL-aware, durable replacement protocol before enabling workers.

Raw job pages and form snapshots expire after 90 days. Archive preserves history but disables new autonomous actions. Permanent deletion removes selected content and linked sensitive audit details, leaves prior immutable envelopes unchanged, appends a content-free deletion-event envelope, rebuilds clean storage through the WAL-aware replacement protocol, clears managed backups that might contain the data, and creates a new clean backup. An interrupted deletion fails closed. Portable copies moved elsewhere remain the user's responsibility.

Human-readable export is distinct from backup and is not restorable. It contains only user-selected, privacy-filtered data and excludes credentials, cookies, sessions, and unrelated secrets.

Secrets use an operating-system credential vault. SQLite stores only opaque provider-and-purpose-scoped references. Live secret values never enter persistence records, exports, logs, errors, or tests. The first version relies on OS account security, user-only permissions, screen locking, and full-disk encryption for the active database and managed local backups; it does not add a separate application unlock password.

## Failure handling

- External calls use timeouts, bounded retries with backoff, and rate-limit awareness.
- Validation failures return actionable, field-specific errors and preserve the draft.
- Partial workflows persist the last safe state and can resume.
- Submission attempts store a redacted receipt or failure reason.
- Correlation identifiers connect events without exposing private content.
- A circuit breaker or manual disable control can suspend a malfunctioning adapter.
- Unsupported or changed external forms fail closed before submission.
- Corrupt, unsafe, locked, or unsupported storage fails closed before autonomous workers start.
- A credential-vault failure pauses only its dependent integration and emits a redacted event.
- Low disk space or a required-backup failure blocks migration, restore, permanent deletion, and other maintenance that could reduce recoverability.
- A stable provider idempotency key is reused where supported, and an `in_flight` claim is persisted before the external call.
- A post-submit/pre-receipt crash that may have reached the provider becomes `indeterminate`; automatic replay stays blocked pending provider reconciliation or explicit human resolution.

## Testing architecture

- **Unit:** schemas, policies, score factors, evidence selection, claim validation, and state transitions.
- **Contract:** each adapter against synthetic fixtures and deterministic provider doubles.
- **Integration:** discovery through `ready-for-review`, including failure and resume paths.
- **End to end:** a synthetic candidate and job; no live submission in default automation.
- **Security:** secret scanning, redaction, malicious job content, authorization gates, WAL-bearing recovery, and post-submit crash tests that prove duplicate-submission resistance.
- **Documentation:** relative links, capability-status accuracy, and runnable command checks.

## Evolution rules

1. Domain packages communicate through documented interfaces.
2. Provider-specific data is translated at adapter boundaries.
3. New integrations require an upstream and compliance evaluation.
4. New automation cannot weaken review, audit, or idempotency guarantees.
5. Splitting a package into a service requires a measured operational or security need, not anticipation alone.
6. Changing the persistence security, migration, backup, retention, or deletion guarantees requires a superseding architecture decision.
