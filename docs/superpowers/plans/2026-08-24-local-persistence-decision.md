# Local Persistence Decision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish and integrate the accepted local SQLite persistence decision for Issue #2, then create the separately scoped implementation issue without adding a runtime database dependency.

**Architecture:** Record SQLite as the local single-device store behind a replaceable persistence boundary, with canonical JSON snapshots, transactional audit and idempotency state, ordered migrations, managed backups, OS-vault credential references, explicit retention, and fail-closed recovery. Keep Issue #2 documentation-only; executable persistence belongs to the follow-up issue.

**Tech Stack:** Markdown architecture decision records, existing repository documentation, GitHub issues, Git, and a standard-library Python link check. No SQLite adapter, ORM, migration framework, encryption package, or other runtime dependency is added.

**Spec:** `docs/superpowers/specs/2026-08-24-local-persistence-design.md`

## Global Constraints

- Personal career and application data is single-device and local-first; automatic cross-device sync is deferred.
- The active database and managed backups rely on the OS account, user-only permissions, and full-disk protection; there is no separate application unlock password in version one.
- Live passwords, API keys, tokens, cookies, sessions, recovery codes, and other secrets stay in an operating-system credential vault and never enter SQLite, backups, human-readable exports, logs, errors, or tests.
- Bounded-autonomous actions must persist the exact approved policy version, decision, durable idempotency-claim state, provider key where supported, receipt when known, and redacted audit-event envelope. Indeterminate outcomes cannot replay automatically.
- The engine retains the seven newest managed local backups and raw source artifacts for 90 days.
- Archive preserves history; permanent deletion removes selected personal content and linked sensitive audit details without rewriting immutable envelopes, appends a deletion envelope, and clears every managed backup that might contain the content before creating a clean replacement backup.
- Nontransactional migration, restore, and permanent deletion use quiesced, same-filesystem, WAL-aware, durable atomic replacement and fail closed on ambiguous recovery state.
- Human-readable export is distinct from backup, includes only selected privacy-filtered data, and excludes credentials, cookies, sessions, and unrelated secrets.
- `packages/core` remains independent of databases, SQL, persistence frameworks, and platform credential providers.
- Issue #2 adds no runtime database dependency and no executable persistence adapter.
- All examples and verification inputs are synthetic and contain no real candidate, application, or credential data.
- Do not copy or adapt third-party code, schemas, fixtures, prompts, or documentation.

---

### Task 1: Publish the Architecture Decision Record

**Files:**
- Create: `docs/decisions/README.md`
- Create: `docs/decisions/0001-local-persistence.md`

**Interfaces:**
- Consumes: the approved requirements in `docs/superpowers/specs/2026-08-24-local-persistence-design.md`.
- Produces: the durable decision identifier `ADR-0001`, the selected storage boundary, the threat model, and the constraints referenced by Task 2 and the follow-up issue in Task 3.

- [ ] **Step 1: Create the decision index**

Create `docs/decisions/README.md` with exactly this content:

```markdown
# Architecture decisions

Architecture decision records document consequential choices, their context, alternatives, and trade-offs. Accepted records are not rewritten to hide a later change; a new record supersedes the old one.

| ID | Decision | Status |
| --- | --- | --- |
| [0001](0001-local-persistence.md) | Local persistence and migration strategy | Accepted |
```

- [ ] **Step 2: Create the accepted decision record**

Create `docs/decisions/0001-local-persistence.md` with the following content. Preserve the concrete limits and exclusions; do not reduce it to “use SQLite.”

```markdown
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
```

- [ ] **Step 3: Verify the decision record is complete and internally linked**

Run:

```bash
grep -nE '^## (Context|Decision|Threats and controls|Consequences|Alternatives considered|Verification obligations for implementation|Follow-up|Detailed design)$' docs/decisions/0001-local-persistence.md
grep -nE 'SQLite|credential vault|seven|90 days|Permanent deletion|residual risks' docs/decisions/0001-local-persistence.md
test -f docs/superpowers/specs/2026-08-24-local-persistence-design.md
git diff --check
```

Expected:

- the first command prints all eight required section headings;
- the second prints at least one line for every required decision term;
- the spec file check exits `0`; and
- `git diff --check` exits `0` with no output.

- [ ] **Step 4: Commit the decision record**

```bash
git add docs/decisions/README.md docs/decisions/0001-local-persistence.md
git commit -m "docs: adopt local SQLite persistence decision"
```

---

### Task 2: Align Public Architecture and Roadmap Documentation

**Files:**
- Modify: `docs/architecture.md`
- Modify: `ROADMAP.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: `ADR-0001` from Task 1.
- Produces: public package ownership, persistence behavior, failure boundaries, roadmap status, and capability claims that agree with the accepted decision.

- [ ] **Step 1: Add the persistence package boundary**

In `docs/architecture.md`, add this section after `packages/shared` and before the application entry points:

```markdown
### `packages/persistence`

Owns repository interfaces, the local SQLite adapter, units of work, migrations, backup and restore, retention and deletion, storage health, and credential references. It depends on domain contracts but domain packages never depend on SQLite or a persistence framework. Live secret values remain in a platform credential vault and never enter persistence records.
```

- [ ] **Step 2: Replace the undecided persistence section with the accepted policy**

Replace the complete `## Persistence and privacy` section in `docs/architecture.md` with:

```markdown
## Persistence and privacy

The accepted [local persistence decision](decisions/0001-local-persistence.md) uses one SQLite database per local workspace behind replaceable repository interfaces. `packages/core` remains database-independent. The database and managed backups live in the operating system's private per-user application-data directory, outside the repository and automatically synchronized folders.

Validated domain aggregates are stored as versioned canonical JSON snapshots with relational control metadata and indexes. Each audit event uses an immutable non-sensitive envelope; optional personal or descriptive content is stored in a separately erasable linked detail. Before an external action, workflow state, the durable idempotency claim, approved policy version and decision, and redacted audit envelope commit atomically. The provider receipt and terminal claim state commit after the external response because that side effect cannot share a SQLite transaction. One engine process may write a database at a time.

Migrations are immutable ordered units with checksums and an application ledger. Pending migrations require a verified pre-migration backup and complete before autonomous workers start. A failed or unsupported migration blocks writes and recovers from a compatible backup rather than running improvised downgrade logic. A nontransactional migration stages a validated replacement on the active database's filesystem. The engine quiesces workers, closes connections, checkpoints or safely disposes WAL state, durably writes and atomically replaces the file, removes stale `-wal` and `-shm` sidecars after old connections close, and durably records parent-directory changes where supported. Ambiguous recovery state fails closed.

The engine creates at most one scheduled managed backup per 24 hours, always backs up before migration, and retains the newest seven. Portable backups are authenticated and password-encrypted, include version and integrity metadata, and exclude credentials. Restore validates a same-filesystem temporary copy and uses the same quiesced, WAL-aware, durable replacement protocol before enabling workers.

Raw job pages and form snapshots expire after 90 days. Archive preserves history but disables new autonomous actions. Permanent deletion removes selected content and linked sensitive audit details, leaves prior immutable envelopes unchanged, appends a content-free deletion-event envelope, rebuilds clean storage through the WAL-aware replacement protocol, clears managed backups that might contain the data, and creates a new clean backup. An interrupted deletion fails closed. Portable copies moved elsewhere remain the user's responsibility.

Human-readable export is distinct from backup and is not restorable. It contains only user-selected, privacy-filtered data and excludes credentials, cookies, sessions, and unrelated secrets.

Secrets use an operating-system credential vault. SQLite stores only opaque provider-and-purpose-scoped references. The first version relies on OS account security, user-only permissions, screen locking, and full-disk encryption for the active database and managed local backups; it does not add a separate application unlock password.
```

- [ ] **Step 3: Extend documented failure handling and evolution rules**

Add these bullets to `## Failure handling` in `docs/architecture.md`:

```markdown
- Corrupt, unsafe, locked, or unsupported storage fails closed before autonomous workers start.
- A credential-vault failure pauses only its dependent integration and emits a redacted event.
- Low disk space or a required-backup failure blocks migration, restore, permanent deletion, and other maintenance that could reduce recoverability.
- A stable provider idempotency key is reused where supported, and an `in_flight` claim is persisted before the external call.
- A post-submit/pre-receipt crash that may have reached the provider becomes `indeterminate`; automatic replay stays blocked pending provider reconciliation or explicit human resolution.
```

Append this numbered item to `## Evolution rules`:

```markdown
6. Changing the persistence security, migration, backup, retention, or deletion guarantees requires a superseding architecture decision.
```

- [ ] **Step 4: Update roadmap and public capability status**

In the Foundation — v0.1 list in `ROADMAP.md`, replace:

```markdown
- Decide local persistence and migrations.
```

with:

```markdown
- Adopt the [local persistence and migration decision](docs/decisions/0001-local-persistence.md).
```

In the project-status table in `README.md`, add this row immediately after canonical candidate and job contracts:

```markdown
| Local persistence and migration strategy | Available | Local SQLite, OS-vault credentials, versioned migrations, managed backups, retention, and deletion boundaries |
```

In the architecture tree in `README.md`, change the `packages/` description so its two wrapped lines read:

```text
packages/      Core domain, persistence, discovery, ranking, documents,
               applications, tracking, and shared contracts
```

- [ ] **Step 5: Run focused documentation checks**

Run:

```bash
if grep -R "The storage technology will be decided" README.md ROADMAP.md docs; then exit 1; fi
grep -n "Local persistence and migration strategy" README.md docs/decisions/README.md
grep -n "local persistence decision" ROADMAP.md docs/architecture.md
python -c 'from pathlib import Path; import re; files=[Path("README.md"),Path("ROADMAP.md"),Path("docs/architecture.md"),Path("docs/decisions/README.md"),Path("docs/decisions/0001-local-persistence.md")]; missing=[]; pattern=re.compile(r"\[[^]]+\]\(([^)]+)\)"); [(missing.append(f"{source}:{target}")) for source in files for target in pattern.findall(source.read_text(encoding="utf-8")) if not target.startswith(("http://","https://","#")) and not (source.parent / target.split("#",1)[0]).resolve().exists()]; assert not missing, missing'
git diff --check
```

Expected:

- the obsolete undecided sentence is absent;
- the two `grep -n` commands print the intended cross-document references;
- the Python link check exits `0` with no missing paths; and
- `git diff --check` exits `0` with no output.

- [ ] **Step 6: Confirm Issue #2 did not add runtime code or dependencies**

Run:

```bash
git diff --name-only HEAD~1
git diff --name-only HEAD~1 | grep -Ev '^(README\.md|ROADMAP\.md|docs/)' && exit 1 || true
git diff -- packages/core/pyproject.toml
```

Expected:

- changed paths are limited to `README.md`, `ROADMAP.md`, and `docs/`;
- the dependency guard emits no unexpected path; and
- the `pyproject.toml` diff is empty.

- [ ] **Step 7: Commit the aligned public documentation**

```bash
git add README.md ROADMAP.md docs/architecture.md
git commit -m "docs: align architecture with local persistence decision"
```

---

### Task 3: Create the Test-Driven Persistence Follow-Up Issue

**Files:**
- No repository files change in this task.
- Create one public GitHub issue in `lulobello/autonomous-career-engine`.

**Interfaces:**
- Consumes: the security, migration, backup, retention, deletion, and verification obligations in `ADR-0001`.
- Produces: one open Foundation — v0.1 implementation issue with title `Implement the local SQLite persistence foundation`, milestone number `1`, and dependencies `#1` and `#2`.

- [ ] **Step 1: Create the follow-up issue with exact scope**

Use the connected GitHub issue-creation operation with:

- repository: `lulobello/autonomous-career-engine`;
- title: `Implement the local SQLite persistence foundation`;
- milestone: `1`;
- labels: `enhancement`, `area: architecture`, `area: privacy`; and
- body:

```markdown
## Why

ADR-0001 selects local SQLite persistence, but Issue #2 deliberately records the decision without adding a runtime adapter. The first executable persistence foundation must prove migrations, crash safety, recovery, privacy, and credential separation before autonomous workflows depend on it.

## Scope

Create `packages/persistence` with a SQLite connection and unit-of-work boundary, an immutable migration ledger, storage health checks, managed and portable backup and restore primitives, raw-artifact retention, immutable audit-event envelopes with erasable sensitive details, WAL-aware permanent-deletion rebuilding, credential references, durable external-action claims and reconciliation, and repository support for the existing candidate-profile and canonical-job contracts. Use only synthetic local data and provider doubles.

## Acceptance criteria

- [ ] `packages/core` has no SQLite or persistence-framework dependency.
- [ ] Candidate profiles and canonical jobs round-trip through validated versioned JSON snapshots.
- [ ] Local multi-record writes atomically persist workflow state, a durable idempotency claim, the exact policy version and decision, and a redacted audit-event envelope.
- [ ] Audit envelopes remain immutable and non-sensitive while linked sensitive audit details can be erased without rewriting prior envelopes; permanent deletion appends a content-free deletion-event envelope.
- [ ] Ordered migrations record checksums and are tested from every supported prior schema.
- [ ] Nontransactional migration recovers to a validated replacement or known-good original or backup after interruption; ambiguous state fails closed.
- [ ] Unknown future versions, modified migrations, corruption, unsafe permissions, and a second writer fail closed.
- [ ] Managed backups use consistent snapshots, run at most once in any 24-hour period and before migration, and retain the newest seven.
- [ ] Portable backups are authenticated and password-encrypted, exclude credentials, and reject wrong passwords and tampering before restore.
- [ ] Restore validates a same-filesystem temporary copy and never damages the active database on validation failure or interruption.
- [ ] Nontransactional migration, restore, and permanent deletion crash tests use a WAL-bearing database and prove workers are quiesced, connections are closed, WAL state is checkpointed or safely disposed, replacement is same-filesystem and durable with its parent directory where supported, and stale `-wal`/`-shm` sidecars are removed.
- [ ] Raw artifacts expire after 90 days and repeated maintenance is idempotent.
- [ ] Permanent deletion removes selected payloads and linked sensitive audit details, preserves immutable envelopes, clears affected managed backups, and creates a clean backup.
- [ ] SQLite, backups, logs, errors, and tests never contain configured secret values; only opaque OS-vault references are stored.
- [ ] External-action claims persist `claimed`, `in_flight`, `succeeded`, `failed`, or `indeterminate` and reuse a stable provider idempotency key where supported.
- [ ] A post-submit/pre-receipt crash that may have reached the provider becomes `indeterminate`; automatic replay remains blocked until provider reconciliation or explicit human resolution.
- [ ] Crash and retry tests prove the last committed state survives and duplicate external actions cannot be created.
- [ ] CI runs without network access, live credentials, real candidate data, or external submission.

## Out of scope

- Cloud or multi-user storage.
- Automatic cross-device synchronization.
- A web interface.
- Live provider credentials or ATS submission.
- Application-level encryption of the active database.
- A full ORM or migration framework without separately demonstrated need.
- Tables or repository methods for domain contracts that do not yet exist.

## Dependencies

#1, #2

## Architecture decision

Follow `docs/decisions/0001-local-persistence.md`. Changing its security, migration, backup, retention, or deletion guarantees requires a superseding architecture decision.
```

- [ ] **Step 2: Verify the created issue**

Fetch the issue returned by the create operation and confirm:

- state is `open`;
- title exactly matches `Implement the local SQLite persistence foundation`;
- milestone is Foundation — v0.1 (`1`);
- all three requested labels are present;
- the body contains `#1, #2` and `docs/decisions/0001-local-persistence.md`;
- the body explicitly covers authenticated password-encrypted portable backups, wrong-password and
  tamper rejection, the 24-hour schedule, policy version and decision fields, immutable audit
  envelopes with erasable details, nontransactional and WAL-aware recovery, and indeterminate
  external-action reconciliation with automatic-replay blocking; and
- the canonical URL belongs to `https://github.com/lulobello/autonomous-career-engine/issues/`.

If any field differs, update that same issue and fetch it again. Do not create a duplicate issue.

- [ ] **Step 3: Record the follow-up URL for the final Issue #2 pull request**

Keep the canonical issue URL in the execution report and include it in the Issue #2 pull-request body under a `Follow-up` heading. No repository file needs a volatile issue number.

---

## Spec coverage map

| Approved spec section | Implemented by |
| --- | --- |
| Purpose, design goals, and user-approved operating policy | Task 1 ADR context and decision; Task 2 README capability status |
| Selected approach | Task 1 ADR decision and alternatives |
| Package and dependency boundaries | Task 1 ADR decision; Task 2 package-boundary addition; Task 3 implementation scope |
| Storage representation | Task 1 immutable-envelope/erasable-detail decision; Task 3 round-trip, redaction, and audit-detail acceptance criteria |
| Transaction and autonomy rules | Task 1 durable claim-state decision; Task 2 failure handling; Task 3 provider-key, indeterminate-reconciliation, locking, and crash criteria |
| Migration protocol | Task 1 WAL-aware replacement decision and verification obligations; Task 2 persistence section; Task 3 transactional and nontransactional recovery criteria |
| Backup and restore | Task 1 24-hour, encryption, and WAL-aware restore decision; Task 2 persistence section; Task 3 wrong-password, tamper, and crash criteria |
| Retention, archive, export, and deletion | Task 1 immutable-envelope deletion and export boundary; Task 2 public persistence section; Task 3 audit-detail, managed-copy, and WAL-aware deletion criteria |
| Credential boundary | Task 1 ADR decision and threat controls; Task 2 package, persistence, and failure sections; Task 3 secret-exclusion criterion |
| Local-data threat model | Task 1 threats and controls; Task 2 public persistence and failure boundaries |
| Failure behavior | Task 1 threats and verification obligations; Task 2 failure handling; Task 3 fail-closed criteria |
| Verification strategy for the follow-up implementation | Task 1 verification obligations; Task 3 exact acceptance criteria |
| Alternatives considered | Task 1 alternatives |
| Acceptance-criteria mapping and Issue #2 deliverables | Tasks 1–3 plus the final acceptance gate |

---

## Final acceptance gate

After all three tasks, run:

```bash
git status --short --branch
git diff --check 0027762..HEAD
git diff --name-only 0027762..HEAD
grep -RInE '\b(TBD|TODO|FIXME)\b' docs/decisions docs/architecture.md README.md ROADMAP.md || true
python -c 'from pathlib import Path; import re; files=[Path("README.md"),Path("ROADMAP.md"),Path("docs/architecture.md"),Path("docs/decisions/README.md"),Path("docs/decisions/0001-local-persistence.md")]; missing=[]; pattern=re.compile(r"\[[^]]+\]\(([^)]+)\)"); [(missing.append(f"{source}:{target}")) for source in files for target in pattern.findall(source.read_text(encoding="utf-8")) if not target.startswith(("http://","https://","#")) and not (source.parent / target.split("#",1)[0]).resolve().exists()]; assert not missing, missing'
```

Expected:

- the branch is clean;
- whitespace and relative-link checks pass;
- changed files are the approved spec, plan, ADR index, ADR, architecture, roadmap, and README only;
- no unresolved planning placeholders remain in the public decision documentation; and
- the execution report includes the verified follow-up issue URL.

Request a whole-branch code/documentation review against Issue #2 and the approved spec. Fix every Critical or Important finding before presenting branch-integration options. The pull request must state that no runtime dependency or database adapter was added, list the documentation checks, link the follow-up implementation issue, and close Issue #2.
