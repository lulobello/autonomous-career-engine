# Local Persistence and Migration Strategy

**Status:** Approved for Issue #2 decision implementation

**Approved:** 2026-08-24

**Repository milestone:** Foundation — v0.1

## Purpose

Issue #2 decides how Autonomous Career Engine will preserve private candidate data,
jobs, application workflow state, automation policy, and audit history on one computer.
The decision must support unattended, crash-safe operation without turning the project
into a cloud service or coupling the domain contracts to a database.

This design selects SQLite behind a replaceable persistence boundary. It defines the
storage shape, migration protocol, credential boundary, backup and restore behavior,
retention and deletion rules, failure handling, threat model, and verification required
before a runtime adapter is implemented.

Issue #2 records the decision and its constraints. It does not yet add a database
adapter or runtime database dependency. A follow-up implementation issue will build the
adapter test-first against this approved contract.

## Design goals

1. Keep personal career and application data local by default.
2. Let autonomous workflows resume safely after interruption.
3. Prevent retries from creating duplicate applications or audit events.
4. Keep `packages/core` independent of databases and storage frameworks.
5. Make migrations ordered, observable, and testable from every supported version.
6. Provide automatic recovery points without silently copying data to the cloud.
7. Make archive, retention, export, restore, and permanent deletion behavior explicit.
8. Let integrations retrieve approved credentials without storing secrets in SQLite.
9. Fail closed when stored data, migrations, credentials, or filesystem state are unsafe.

## User-approved operating policy

- Storage is single-device and local-first. Automatic cross-device sync is deferred.
- The application does not add a separate database-unlock password in the first version.
- The operating-system account, user-only file permissions, and full-disk protection are
  the database-at-rest security boundary.
- API keys and passwords may support unattended operation, but live secret values stay in
  the operating-system credential vault rather than the database.
- Bounded-autonomous submission is permitted only inside preapproved policies. Storage
  must persist those policies, their versions, decisions, durable idempotency claims, and
  audit events, including indeterminate outcomes that must not be replayed automatically.
- The engine keeps the seven newest managed local backups and supports an explicit portable
  backup.
- Archive preserves history. Permanent deletion removes selected personal content from the
  live database and every managed backup that might contain it.
- Raw job pages and application-form snapshots expire after 90 days. Normalized job and
  application history remain until archive or permanent deletion.

## Selected approach

Use one SQLite database per local workspace through a narrow persistence package and
repository interfaces. SQLite provides transactions, uniqueness constraints, indexes,
integrity checking, and a consistent backup mechanism without a database server. It is
available through Python's standard library and does not require an ORM.

The first implementation will use lightweight, ordered SQL migrations with an application-
owned runner. A full ORM and migration framework are deliberately deferred. If later
requirements justify cloud or multi-user storage, adapters can implement the same repository
contracts without changing the canonical domain models.

The database file must live in the operating system's per-user application-data directory,
not inside the Git repository, a downloads directory, or an automatically synchronized
folder. Tests use isolated temporary directories and synthetic data.

## Package and dependency boundaries

`packages/core` remains the authority for candidate and canonical-job validation and must not
import SQLite, SQL, a persistence package, or a credential provider.

A future `packages/persistence` package will own:

- repository interfaces and a unit-of-work boundary;
- the SQLite adapter and connection policy;
- schema migrations and the migration ledger;
- backup, restore, integrity checking, retention, and deletion;
- storage-specific error types and health reporting; and
- credential references and a credential-gateway interface, but never live secret values.

Application entry points compose domain packages with a persistence adapter and a platform
credential gateway. Discovery, ranking, documents, applications, and tracking consume
repository interfaces; they do not execute SQL or depend on SQLite-specific models.

The initial repository surface will be separated by purpose rather than exposed as a generic
key/value API:

- candidate profiles and their evidence;
- canonical jobs and raw-source artifacts;
- applications, workflow state, and bounded-automation policies;
- immutable non-sensitive audit-event envelopes and separately erasable sensitive details;
- idempotency claims and submission receipts; and
- retention, backup, and storage health operations.

Interfaces will be finalized alongside the first consuming vertical slice. This decision fixes
their behavioral boundary, not every method name before a consumer exists.

## Storage representation

Validated domain aggregates are stored as immutable, versioned JSON snapshots plus a small
set of indexed relational columns. The JSON representation is produced only from authoritative
Pydantic models. Reads parse and revalidate the snapshot before returning it to domain code.

Each aggregate envelope records:

- its stable identifier;
- public contract name and contract version;
- canonical JSON payload;
- created and updated timestamps;
- archive or deletion state where applicable; and
- an optimistic revision number for safe replacement.

Indexed columns support identity lookup, workflow queues, retention deadlines, status filters,
source deduplication, and ordering without duplicating domain validation in SQL. The JSON
snapshot remains the full domain record. Database constraints still enforce storage-level
invariants such as primary keys, unique idempotency keys, non-null control metadata, and valid
foreign-key relationships.

Every audit event has an immutable, non-sensitive envelope containing an event identifier,
opaque aggregate and actor or automation-policy references, event type, exact policy version and
decision when applicable, correlation and idempotency identifiers, timestamp, and redacted control
metadata. Optional descriptive or personal content belongs in a separately stored, linked sensitive
detail record. An update creates a new validated aggregate snapshot and its envelope in one
transaction. Envelopes are append-only and are never rewritten; sensitive detail records may be
erased by retention or permanent deletion without changing their envelopes.

Raw source artifacts are stored separately from normalized records with capture time,
content type, content hash, source reference, privacy classification, and `expires_at`. They
must not be copied into audit metadata. Their default expiry is 90 days from capture.

Credential records contain only an opaque vault key, provider identifier, purpose, optional
account label, creation time, and last successful access time. Secret material, recovery codes,
session cookies, and tokens never appear in SQLite, backups, exports, logs, or test fixtures.

## Transaction and autonomy rules

Every local multi-record state change runs inside one unit of work. Before an external action, one
transaction commits the new aggregate snapshot, workflow transition, exact policy version and
decision, durable idempotency claim, and corresponding audit envelope. Either all local records
commit or none do. A provider response is recorded afterward with the receipt and resulting claim
state because an external side effect cannot share the SQLite transaction.

An idempotency key is unique within its operation scope and is also sent as the provider's
idempotency key when that provider supports one. Claims use durable states including `claimed`,
`in_flight`, `succeeded`, `failed`, and `indeterminate`. The engine commits `in_flight` before the
provider call and commits `succeeded` with the redacted receipt only after the response is durably
stored. Retrying after a timeout or crash first reads the prior claim and result.

If a provider might have accepted an action but the engine did not durably store its receipt, the
claim becomes `indeterminate`. Automatic replay is blocked even when the provider lacks an
idempotency facility. Provider-side lookup or another reconciliation mechanism may resolve the
claim to `succeeded` or `failed`; otherwise an explicit human resolution is required. A retry cannot
create a second submission merely because the caller did not receive the original response.

Bounded-autonomous policies are versioned snapshots. Each autonomous decision records the exact
policy version used. Updating a policy affects future decisions only; it does not rewrite past
audit events or authorize an in-flight action retroactively.

The first version permits one engine process per database. Startup acquires an application lock
before enabling schedulers or autonomous workers. A second process may open a documented read-only
diagnostic path if safe, but it cannot perform writes or external actions.

The SQLite implementation will enable foreign-key enforcement and use write-ahead logging for
reliable local readers and one writer. Durability settings favor preserving approved workflow
state over maximum write throughput. Busy waits are bounded; lock exhaustion becomes an explicit
retryable storage error rather than an indefinite hang.

## Migration protocol

Database schema version and public contract version are independent. A database layout can change
without changing the meaning of a candidate-profile or canonical-job schema, and a new public
contract version can be stored without renumbering unrelated SQL migrations.

Migration identifiers are immutable, ordered names such as `0001_initial`. The migration ledger
records identifier, description, checksum, and application timestamp. Applied migration contents
must never be edited. A changed checksum is treated as repository or database corruption and blocks
writes.

Startup follows this sequence:

1. acquire the single-engine lock;
2. confirm the database path and file permissions are safe;
3. open the database and run SQLite integrity checks appropriate to startup;
4. read the migration ledger and compare it with bundled migrations;
5. reject databases newer than the running application;
6. create a managed pre-migration backup when migrations are pending;
7. apply each pending migration in order within a transaction; and
8. validate the upgraded schema and representative stored payloads before enabling workers.

A failed migration rolls back its transaction and leaves autonomous work disabled. Recovery uses
the verified pre-migration backup. Normal operation does not run improvised down-migrations;
restoring a compatible backup is safer and testable.

A migration that cannot be transactional must build and validate a new database on the same
filesystem as the active database. Before replacement, the engine quiesces workers, closes all
connections, and checkpoints the active database or otherwise safely disposes its WAL state. It
durably writes the replacement file and, where supported, its parent-directory entry before and
after atomic replacement, then removes stale `-wal` and `-shm` sidecars only after all old
connections are closed. An interruption recovers to either the validated replacement or the
known-good original or pre-migration backup; ambiguous state fails closed before workers start.

Supported release upgrades must have tests beginning from every maintained prior database version.
Very old versions may require a documented staged upgrade rather than keeping unlimited migration
paths forever.

## Backup and restore

Managed backups are consistent SQLite snapshots created through SQLite's backup mechanism, not a
filesystem copy of an open database. The engine creates at most one scheduled backup in any 24-hour
period after confirming database health, and always creates a backup before migration. Pre-migration
backups participate in the same seven-backup retention limit after the upgrade is verified.

Managed backups remain on the same computer under the private application-data directory. They rely
on the same operating-system and full-disk security boundary as the active database. Backup filenames
contain only timestamps and storage versions, never candidate names, employers, job titles, or email
addresses.

A manual portable backup is an authenticated, password-encrypted bundle containing:

- one consistent database snapshot;
- a manifest with application, storage-schema, and contract versions;
- file hashes and creation time; and
- restore instructions and a declaration that credentials are excluded.

Version one does not offer an unencrypted portable backup. Cryptographic implementation must use a
maintained, independently reviewed library that provides authenticated encryption and a password-
based key derivation function. Dependency and algorithm selection will be recorded and reviewed when
the portable-backup implementation is planned; the project will not design its own cryptography.

Restore never writes directly over the active database. It decrypts when applicable, verifies the
manifest and hashes, opens and migrates a temporary copy if supported, validates database integrity
and stored domain payloads, and creates a backup of the current healthy database. The temporary
copy is staged on the active database's filesystem. Before replacement, the engine quiesces workers,
closes connections, checkpoints or safely disposes active WAL state, durably writes the replacement
file and parent-directory entry where supported, atomically replaces the active file, removes stale
`-wal` and `-shm` sidecars, and durably records the new directory state where supported. Failure or
an interruption recovers to a fully validated old or new database and never enables workers on an
ambiguous mixture.

## Retention, archive, export, and deletion

A maintenance task runs at startup and at least daily while the engine is active. It removes raw
source artifacts whose `expires_at` is past, prunes managed backups beyond the newest seven, and
records content-free maintenance events. Repeating the task is idempotent.

Archiving removes an item from active queues and default views while preserving its normalized
record, workflow history, audit events, and permitted supporting data. Archived records cannot
trigger new autonomous actions unless explicitly restored.

Permanent deletion is a distinct, irreversible operation. It:

1. stops and invalidates pending autonomous actions for the selected subject;
2. deletes selected personal payloads, related raw artifacts, and linked sensitive audit-detail
   records from the live database while leaving immutable audit-event envelopes unchanged;
3. appends a new content-free deletion-event envelope;
4. builds and validates a clean replacement database containing only retained records and audit
   envelopes, then uses the same quiesced, same-filesystem, WAL-aware, durable atomic-replacement
   protocol as restore;
5. deletes all managed backups that may contain the removed content; and
6. creates one new clean managed backup after database integrity validation.

An interrupted deletion fails closed and resumes or recovers without reopening a database or
managed backup set that is ambiguously only partly scrubbed.

Manual portable backups copied outside the managed directory cannot be deleted by the engine. The
user interface and documentation must state this before creation and permanent deletion.

Human-readable data export is separate from a restorable backup. A future export function will emit
only user-selected, validated, versioned, privacy-filtered records without internal idempotency
material, vault references, credentials, cookies, sessions, or unrelated secrets. This issue defines
the boundary but does not implement the product export format.

## Credential boundary

Unattended integrations retrieve credentials through an operating-system credential gateway after
one-time setup. The database holds an opaque reference that is useless without access to the same OS
account and vault. Credential access is limited to the provider and purpose recorded for that
reference.

Credential retrieval failures are typed and never include the secret value. An unavailable, expired,
or rejected credential pauses only the affected adapter or action and produces an actionable,
redacted audit event. Unrelated safe work may continue.

The first version does not persist secrets as a fallback when a platform vault is unavailable. A
platform without an approved secure credential backend cannot run unattended authenticated adapters.

## Local-data threat model

### Protected assets

- candidate identity, contact details, career history, evidence, and generated materials;
- discovered jobs, private notes, application answers, application status, and outcomes;
- automation policies, idempotency keys, submission receipts, and audit events;
- raw job pages and application-form snapshots; and
- API keys, passwords, tokens, cookies, and recovery material held outside SQLite.

### Threats addressed

- accidental commit or inclusion of live data in public fixtures;
- secrets leaking through the database, backups, exports, logs, exceptions, or filenames;
- partial writes and duplicate actions after crashes or retries;
- database corruption, incompatible versions, modified migrations, or unsafe restores;
- a second local engine issuing conflicting autonomous actions;
- indefinite retention of raw external content;
- deleted personal content surviving in managed backups; and
- unauthorized autonomous action caused by missing or changed policy state.

### Controls

- application data outside the repository with user-only permissions;
- validated immutable payloads and transactional writes;
- immutable redacted audit envelopes, erasable sensitive details, and unique idempotency constraints;
- startup integrity, migration, permission, and version gates;
- managed backup rotation and staged restore;
- operating-system credential storage with opaque database references;
- single-engine locking and bounded database waits;
- explicit policy versions and fail-closed autonomous decisions; and
- automatic raw-data expiry and destructive deletion of managed recovery copies.

### Accepted residual risks

The application database and managed local backups are not independently encrypted in version one.
Anyone who can access the user's unlocked OS account or an unencrypted disk may read them. The
documentation must recommend a protected OS account, full-disk encryption, screen locking, and
careful handling of manually exported backups.

Replacing and deleting managed files prevents the application from reusing SQLite pages that held
deleted content, but consumer filesystems, SSD firmware, operating-system snapshots, and unrelated
backup software may retain physical remnants outside the engine's control. The documentation must
state this limit rather than promise forensic erasure the application cannot verify.

The system cannot erase portable backups the user moved elsewhere. It also cannot protect data after
an approved integration sends it to a job source or ATS; later adapters must document destination
retention and access rules before use.

## Failure behavior

Storage failures are typed as configuration, permission, locked, busy, corrupt, unsupported-version,
migration, integrity, backup, restore, not-found, conflict, or unavailable-credential errors. Error
messages identify the operation and safe recovery action without including record payloads or secrets.

Database corruption, unsafe permissions, an unknown future schema, migration checksum mismatch,
failed migration, failed restore validation, or inability to acquire the engine lock prevents
autonomous writes and external actions. The engine preserves available evidence and offers a
read-only diagnostic or recovery path when that path can be proven safe.

An `in_flight` external-action claim found after interruption is reconciled with the provider when
possible. If the provider may have accepted the action and no receipt was durably stored, the claim
is marked `indeterminate`; automatic replay remains blocked until provider reconciliation or an
explicit human resolution records a safe terminal result.

Low disk space or inability to create a required backup blocks migrations, restore, permanent
deletion, and other maintenance operations that could reduce recoverability. Ordinary reads may
continue when SQLite reports them as safe.

A credential-vault failure pauses only its dependent integration. A retention failure does not erase
unrelated data, but it raises a visible health condition and prevents claims that expired raw data was
successfully removed.

## Verification strategy for the follow-up implementation

All tests use synthetic records and isolated temporary application directories. The runtime adapter
must include:

1. repository contract tests for save, retrieve, replace, archive, delete, list, and optimistic
   revision conflicts;
2. transaction tests proving a failed multi-record operation leaves no partial state;
3. idempotency and external-action tests proving durable claim-state transitions, provider
   idempotency-key reuse where supported, post-submit/pre-receipt crash handling, reconciliation,
   and automatic-replay blocking for indeterminate results;
4. audit tests proving envelope order and immutability, policy-version and decision capture,
   redaction, and erasure of linked sensitive details without rewriting envelopes;
5. migration tests from every supported prior schema, including checksum mismatch, unknown future
   versions, rollback, WAL-bearing crashes, and recovery through nontransactional copy-and-replace;
6. backup tests for 24-hour scheduling, seven-copy rotation, consistent snapshots, and pre-migration
   recovery;
7. portable-backup tests for encryption, wrong passwords, tampering, manifest validation, and
   exclusion of credential values;
8. restore tests proving the active database remains untouched on every validation failure and that
   WAL-bearing crashes cannot expose stale sidecars or a mixed old/new database;
9. retention tests for 90-day raw-data expiry and idempotent maintenance;
10. permanent-deletion tests proving live payload and sensitive audit-detail removal, immutable
    envelope preservation, managed-backup clearing, clean-backup recreation, and WAL-bearing crash
    recovery;
11. credential-boundary tests proving database files, backups, logs, and exceptions never contain
    configured secret values; and
12. concurrency and crash tests proving a second engine cannot write and interrupted operations
    preserve the last committed state.

CI must run database tests without network access, live credentials, real candidate data, or external
application submission.

## Alternatives considered

### Separate JSON or JSON Lines files

This minimizes storage code and makes individual records easy to inspect. It was rejected as the
primary store because atomic multi-record transitions, indexes, uniqueness, migrations, concurrent
background tasks, backup consistency, and recovery would require substantial custom machinery.

### SQLite with a full ORM and migration framework

This supplies mature mapping and migration APIs but adds abstractions and dependencies before query
patterns or cloud portability justify them. It was rejected for the first implementation. The narrow
repository boundary permits adopting one later if complexity demonstrates a need.

### One SQLite table per nested domain object

Fully normalized relational storage enables detailed SQL queries but duplicates the public Pydantic
model structure and increases migration work whenever nested contracts evolve. It was rejected in
favor of validated JSON aggregate snapshots with selected relational indexes and control tables.

### Encrypted application database in version one

Application-level database encryption protects against some offline file access but introduces key
recovery, unattended unlock, platform integration, dependency, backup, and migration complexity. It
was deferred in favor of the OS account, user-only permissions, and full-disk encryption boundary.
Portable backups remain encrypted because they are designed to leave the managed directory.

### Automatic cloud synchronization

Cloud sync improves multi-device access but creates authentication, remote retention, conflict,
availability, and privacy requirements unrelated to the first local workflow. It was deferred. The
repository boundary keeps a later synchronized adapter possible without changing `packages/core`.

## Acceptance-criteria mapping

| Issue #2 acceptance criterion | Design response |
| --- | --- |
| Compare SQLite and file-backed alternatives | Selected SQLite; alternatives evaluate JSON/JSONL, a full ORM, normalized relational storage, encryption, and cloud sync. |
| Identify credentials and sensitive application content | The threat model enumerates candidate, application, audit, raw-source, automation, receipt, and credential assets with explicit boundaries. |
| Make migrations versioned and testable | Immutable ordered migrations, checksums, a ledger, pre-migration backups, rollback rules, and tests from every supported prior version. |
| Define backup, export, retention, and deletion | Seven local backups, encrypted portable backup, staged restore, 90-day raw retention, archive, and destructive deletion across managed copies. |
| Add no runtime database dependency before acceptance | Issue #2 records the decision only; the SQLite adapter and any reviewed dependencies belong to a follow-up implementation issue. |

## Consequences and limits

SQLite provides a strong local foundation with little operational burden, but one database and one
writer are not a hosted multi-user architecture. JSON snapshots reduce relational migration churn but
make arbitrary analytics less convenient; selected indexes and future derived views should answer
measured needs rather than pre-normalizing every field.

Relying on OS and disk security means the user must secure the device. Credential-vault integration is
platform-specific and will require adapters. Permanent deletion intentionally sacrifices old managed
recovery points to honor the deletion promise. Manual portable backups remain outside the engine's
control.

These trade-offs favor privacy, autonomous reliability, and a credible first vertical slice over
speculative cloud scale.

## Issue #2 deliverables

The decision implementation will:

1. commit this approved design specification;
2. add a concise architecture decision record under `docs/decisions/`;
3. update `docs/architecture.md` with the selected persistence, credential, backup, retention, and
   failure boundaries;
4. update roadmap or contributor links only where needed to make the decision discoverable; and
5. create a focused follow-up issue for the test-driven SQLite persistence foundation.

No SQLite adapter, migration runner, credential integration, encryption dependency, or production
database file is added in Issue #2.

## Definition of done

Issue #2 is complete when the decision record and architecture documentation agree; SQLite and
file-backed alternatives are compared; the threat model covers secrets and personal application
content; migration, backup, restore, export, retention, archive, and deletion behaviors are explicit;
future verification is observable and synthetic; the follow-up implementation issue is scoped; all
documentation checks pass; and the work is merged without runtime storage dependencies or real data.
