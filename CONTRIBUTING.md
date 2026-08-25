# Contributing to Autonomous Career Engine

Thank you for helping build a transparent, responsible career workflow. Contributions are welcome from engineers, designers, researchers, career practitioners, and job seekers.

## Before you start

1. Read the [project status](README.md#project-status), [roadmap](ROADMAP.md), and [architecture](docs/architecture.md).
2. Search open and closed issues before creating a new one.
3. For substantial changes, open an issue first so the interface, safety constraints, and scope can be agreed before implementation.
4. Never post real resumes, credentials, application answers, access tokens, or other personal data in an issue, test, commit, or pull request.

## Choosing work

- `good first issue` marks bounded work with no live credentials or personal data.
- `help wanted` means the interface is stable enough for outside implementation.
- Area labels such as `area: ranking` show the component that owns the change.
- Integration proposals must use the integration issue form and document access terms, rate limits, and data handling.

## Development workflow

1. Fork the repository.
2. Create a focused branch from `main`, such as `feat/job-schema` or `docs/ranking-explanation`.
3. Keep commits small and use clear imperative messages.
4. Add or update tests for behavior changes.
5. Update documentation when an interface, workflow, status, or limitation changes.
6. Open a pull request using the provided template.

The executable core package has its setup and verification commands in the
[core package README](packages/core/README.md). Other packages remain
documentation-only; do not introduce a framework or dependency manager in an
unrelated pull request.

## Design expectations

Contributions should preserve these invariants:

- candidate claims are traceable to verified evidence;
- fit scores expose factors, evidence, and uncertainty;
- model output is parsed and validated as untrusted input;
- submission requires review by default;
- retries cannot cause duplicate applications;
- integrations are replaceable adapters, not domain dependencies;
- public fixtures are synthetic;
- logs exclude secrets and personal application content.

## Tests

Each implemented package must include the narrowest useful tests:

- unit tests for domain policies and pure transformations;
- contract tests for adapter interfaces using synthetic or recorded-safe fixtures;
- integration tests for cross-package workflows;
- end-to-end tests only for privacy-safe synthetic scenarios.

Pull requests should explain what was tested and show the exact commands and results. Live integration tests must be opt-in and must not run for forks by default.

## Documentation and status claims

Do not mark a capability **Available** in the README until its implementation, tests, and user documentation are merged. Use **Experimental** only for working code whose interface or reliability is not yet stable.

Architecture decisions that change a public interface or schema should include a
short decision record under `docs/` describing context, alternatives, and
consequences. Changes to public core schemas must regenerate `schemas/v1` and
preserve the representative v1 fixtures; incompatible changes require a new major
schema directory and migration guidance.

## Third-party material

Do not paste or adapt third-party code, schemas, fixtures, prompts, or documentation until an [upstream evaluation](docs/upstream-evaluation.md) is approved. Ideas may be discussed with citations, but implementation provenance must remain clear.

## Pull-request review

Maintainers review for correctness, scope, tests, privacy, security, provenance, and clarity. A request for changes is part of collaborative development, not a rejection of the contributor.

By participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md) and certify that your contribution may be released under the [Apache License 2.0](LICENSE).
