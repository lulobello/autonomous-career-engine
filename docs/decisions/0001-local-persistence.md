# ADR-0001: Local persistence and migration strategy

**Status:** Accepted

**Date:** 2026-08-24

**Issue:** [#2](https://github.com/lulobello/autonomous-career-engine/issues/2)

## Context

Autonomous Career Engine must preserve private candidate data, jobs, workflow state, approved automation policy, idempotency claims, submission receipts, and audit history across interruptions. The first product is single-user and local-first. Domain contracts must remain independent of storage technology, credentials must support unattended integrations without leaking into the data store, and deletion must account for managed recovery copies.

## Decision

Use one SQLite database per local workspace behind a narrow persistence package and repository interfaces. The database lives in the operating system's private per-user application-data directory, outside the Git repository and automatically synchronized folders. The first version permits one writing engine process per database.

`packages/core` remains database-independent. A future `packages/persistence` package owns the SQLite adapter, unit of work, migrations, backup and restore, retention and deletion, storage health, credential references, and typed storage failures. Application entry points compose this adapter with domain packages and the operating-system credential gateway.

Validated domain aggregates are stored as immutable, versioned canonical JSON snapshots with relational identifiers, timestamps, revision numbers, indexes, uniqueness constraints, and foreign keys for storage-level control data. Reads revalidate snapshots with the authoritative Pydantic models. Each audit event has an immutable, non-sensitive envelope with opaque references, policy version, decision, and redacted control fields when applicable. Optional descriptive or personal content is stored in a separately erasable linked detail record; deletion never rewrites an envelope.

Before an external action, one transaction writes the new snapshot, policy version and decision, durable idempotency claim, and audit envelope. Claims move through durable states including `claimed`, `in_flight`, `succeeded`, `failed`, and `indeterminate`, and use a stable provider idempotency key where supported. The engine commits `in_flight` before submission and records `succeeded` with the receipt afterward. If the provider may have accepted the action but no receipt was durably stored, the claim becomes `indeterminate`; automatic replay is blocked until provider reconciliation or explicit human resolution.

Database migrations are immutable ordered units such as `0001_initial`. A migration ledger records identifier, description, checksum, and application time. Startup rejects changed checksums and newer unsupported databases, creates a managed pre-migration backup, applies pending migrations transactionally, and validates the result before enabling autonomous workers. Recovery uses a verified backup instead of improvised down-migrations. Nontransactional migrations stage and validate a new database on the active database's filesystem; replacement quiesces workers, closes connections, checkpoints or safely disposes WAL state, durably writes the replacement file, atomically replaces it, removes stale `-wal` and `-shm` sidecars after old connections close, and durably records parent-directory changes where supported. Ambiguous recovery state fails closed.

Managed backups are consistent SQLite snapshots. The engine creates at most one scheduled backup per 24 hours and always backs up before migration, retaining the newest seven. A portable backup is an authenticated password-encrypted bundle with version metadata and integrity hashes; it never includes credentials. Restore validates and migrates a same-filesystem temporary copy, then uses the same quiesced, WAL-aware, durable atomic-replacement protocol as nontransactional migration.

Raw job pages and application-form snapshots expire after 90 days. Archive preserves normalized history and audit envelopes while preventing new autonomous actions. Permanent deletion stops pending actions, removes selected personal content and linked sensitive audit details, appends a content-free deletion-event envelope without rewriting prior envelopes, rebuilds a clean database through the WAL-aware replacement protocol, deletes managed backups that might contain the removed content, and creates a new clean backup. Interrupted deletion fails closed. The engine cannot erase portable copies moved outside its managed directory.

Human-readable export is distinct from backup: it contains only user-selected, privacy-filtered data and excludes credentials, cookies, sessions, and unrelated secrets. It is not a restorable storage image.

Passwords, API keys, tokens, cookies, recovery material, and live secret values stay in an operating-system credential vault. SQLite stores only opaque provider-and-purpose-scoped references. If an approved secure vault is unavailable, authenticated unattended adapters cannot run.

The active database and managed local backups are not independently encrypted in version one. They rely on the protected OS account, user-only permissions, screen locking, and full-disk encryption. Portable backups are encrypted because they are intended to leave the managed directory.

## Threats and controls

Protected assets include candidate identity and evidence, application answers and outcomes, generated materials, raw source snapshots, automation policies, idempotency keys, receipts, audit events, and credentials held outside SQLite.

The design addresses accidental repository exposure, secret leakage, partial writes, duplicate actions, incompatible or corrupt databases, modified migrations, conflicting local writers, unsafe restore, indefinite raw-data retention, personal data surviving in managed backups, and autonomous actions using missing or changed policy state.

Controls include storage outside the repository, user-only permissions, validated immutable payloads, transactions, unique idempotency constraints, immutable redacted audit envelopes with erasable sensitive details, startup integrity and version gates, managed backup rotation, staged WAL-aware restore, OS credential storage, single-engine locking, explicit policy versions and decisions, indeterminate-action replay blocking, 90-day raw-data expiry, and destructive deletion of managed recovery copies.

The application cannot protect an unlocked compromised OS account, guarantee forensic erasure from SSD firmware or unrelated system snapshots, erase portable copies moved elsewhere, or control data after an approved integration sends it to a destination. These are documented residual risks, not hidden guarantees.

## Consequences

SQLite provides transactions, integrity checks, indexes, uniqueness, and consistent backup without a server or ORM. JSON aggregate snapshots reduce duplicate mapping and relational migration churn, while selected indexes preserve measured query paths.

The design favors one local writer over hosted multi-user scale. Arbitrary analytics are less convenient than with fully normalized tables. OS-vault integration is platform-specific. Permanent deletion intentionally sacrifices older managed recovery points to honor the deletion promise.

## Alternatives considered

- **Separate JSON or JSON Lines files:** rejected because atomic cross-record state changes, uniqueness, indexes, migrations, backup consistency, and recovery would require substantial custom machinery.
- **SQLite with a full ORM and migration framework:** deferred because it adds abstractions and dependencies before query patterns justify them.
- **Fully normalized domain tables:** rejected because they duplicate nested Pydantic contracts and amplify migrations whenever public schemas evolve.
- **Application-level database encryption in version one:** deferred because unattended unlock and recovery introduce key-management and platform complexity; portable backups remain encrypted.
- **Automatic cloud synchronization:** deferred because it adds remote identity, retention, conflict, availability, and privacy requirements outside the first local workflow.

## Verification obligations for implementation

The follow-up adapter must test repository behavior, transaction rollback, durable idempotency-claim states, the post-submit/pre-receipt crash boundary, provider reconciliation, indeterminate replay blocking, immutable audit-envelope order and redaction, sensitive-detail erasure, migrations from every supported prior version, checksum mismatch, unsupported future versions, nontransactional recovery, the 24-hour and seven-copy backup rules, encrypted portable-backup wrong-password and tamper rejection, staged restore failure, 90-day retention, permanent deletion across managed copies, credential exclusion, single-engine locking, and WAL-bearing crash recovery for migration, restore, and deletion. All tests use synthetic local data with no network access or live credentials.

## Follow-up

Implement the test-driven SQLite persistence foundation in a separate issue. That issue must preserve this decision and may narrow interfaces to actual consumers, but changing the selected security, migration, backup, retention, or deletion guarantees requires a superseding architecture decision.

## Detailed design

See [the approved Issue #2 design](../superpowers/specs/2026-08-24-local-persistence-design.md).
