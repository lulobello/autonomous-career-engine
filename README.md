# Autonomous Career Engine

> Human-centered AI workflows for job discovery, explainable ranking, truthful tailored materials, assisted applications, tracking, and outcome learning.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Project status](https://img.shields.io/badge/status-foundation-orange.svg)](ROADMAP.md)

Autonomous Career Engine is an open-source project for building a more deliberate, transparent job-search workflow. The system is designed to discover opportunities, explain candidate-job fit, draft application materials from verified experience, assist with application forms, track outcomes, and learn which strategies work—without taking control away from the job seeker.

**Foundation stage:** governance, architecture, and the first executable contracts are published; discovery, ranking, documents, applications, and tracking remain unimplemented.

## Project status

| Capability | Status | Planned outcome |
|---|---|---|
| Project governance and contributor workflow | Available | A public, forkable foundation for collaborative development |
| Architecture and safety model | Available | Clear component boundaries, data flow, and review gates |
| Canonical candidate and job contracts | Experimental | Versioned, provenance-aware Pydantic models and generated JSON Schema |
| Job discovery and normalization | Planned | Compliant source adapters and a canonical job schema |
| Explainable fit ranking | Planned | Evidence-backed factors, hard filters, and visible uncertainty |
| Tailored resume and cover-letter generation | Planned | Truth-constrained drafts grounded in verified experience |
| Assisted ATS application workflow | Planned | Review-first form preparation with resumable state |
| Application tracking | Planned | Auditable events, statuses, and outcome capture |
| Outcome learning | Planned | User-approved recommendations based on response patterns |

The status table is intentionally conservative. A capability will move to **Available** only when its implementation, tests, and documentation are present in the repository.

## Why this project exists

Job-search tooling often optimizes for application volume while hiding how matches are scored or what an AI changed. This project explores a different model:

- the user remains the decision-maker;
- ranking explains its evidence and uncertainty;
- generated materials cannot invent qualifications;
- private career data stays local by default;
- external integrations are replaceable and compliance-aware;
- automation is bounded, auditable, and review-first.

## Planned workflow

```text
Candidate profile
      │
      ▼
Discover → Normalize → Filter → Explainable ranking
                                      │
                                      ▼
                           Shortlist and draft
                                      │
                                      ▼
                           Validate every claim
                                      │
                                      ▼
                         Human review and approval
                                      │
                                      ▼
                          Assist, submit, and track
                                      │
                                      ▼
                      Propose outcome-based improvements
```

The default application mode will be `review`. Future `watch` and opt-in `bounded-auto` modes must preserve auditability, submission limits, and explicit user configuration.

## Architecture

The project uses a modular monorepo so the first vertical slice can run as one system while keeping integrations and domain concerns isolated.

```text
apps/          Future API and web entry points
packages/      Core domain, discovery, ranking, documents,
               applications, tracking, and shared contracts
examples/      Synthetic, privacy-safe fixtures and walkthroughs
tests/         Unit, contract, integration, and end-to-end tests
docs/          Architecture, decisions, safety, and provenance
.github/       Contribution templates and community health files
```

Read [the architecture document](docs/architecture.md) for component boundaries, data flow, failure handling, and the trust model.

## Safety and privacy commitments

- **Truth over persuasion:** the system may select and reframe verified evidence, but it must not invent employers, dates, credentials, skills, or achievements.
- **Human review by default:** no application is submitted without approval unless the user has deliberately enabled a bounded policy.
- **Local-first personal data:** resumes, profiles, credentials, and application records are excluded from version control and remain local by default.
- **Untrusted AI output:** model responses are validated against structured schemas and source evidence.
- **Responsible integrations:** adapters must document their access method, applicable terms, rate limits, and data handling.
- **No mass-application promise:** the project does not aim to bypass platform controls or submit indiscriminately.

## Getting involved

There is no production quick start yet because the engine has not been implemented. The best way to participate today is to:

1. Read the [roadmap](ROADMAP.md) and [architecture](docs/architecture.md).
2. Choose a scoped issue from the first milestone.
3. Review [CONTRIBUTING.md](CONTRIBUTING.md).
4. Fork the repository, create a focused branch, and open a pull request.

Issues labeled `good first issue` are intended to be approachable without live service credentials or personal career data.

## Roadmap

- **v0.1 — Foundation:** schemas, configuration, persistence decisions, synthetic fixtures, and a minimal vertical-slice contract.
- **v0.2 — Discover & Rank:** one compliant source adapter, normalization, filtering, and explainable scoring.
- **v0.3 — Tailored Materials:** verified evidence, claim validation, resume export, and grounded cover letters.
- **v0.4 — Apply & Track:** review workflow, an ATS adapter prototype, audit events, and tracking contracts.
- **v0.5 — Learn & Evaluate:** outcome capture, offline evaluation, transparent recommendations, and privacy review.

Detailed outcomes and exclusions are in [ROADMAP.md](ROADMAP.md).

## Upstream research and attribution

This is an original project. Its initial architecture was informed by reviewing the broader open-source job-automation ecosystem, including [AutoApply](https://github.com/AbhishekMandapmalvi/AutoApply). No upstream source code, schemas, fixtures, or documentation have been copied into this repository.

Any future incorporation of third-party material requires the documented [upstream evaluation](docs/upstream-evaluation.md), including license compatibility, provenance, attribution, and security review. Mention of another project does not imply affiliation or endorsement.

## Contributing, security, and community

- [Contributing guide](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Apache-2.0 license](LICENSE)

Contributions, issue reports, design critiques, and responsible integration proposals are welcome.
