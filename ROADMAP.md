# Roadmap

This roadmap describes intended outcomes, not delivery promises. A milestone is complete only when its acceptance criteria are implemented, tested, and documented with synthetic data.

## Foundation — v0.1

**Outcome:** a trustworthy base for the first end-to-end workflow.

- Define canonical candidate-profile and job schemas.
- Decide local persistence and migrations.
- Define configuration and secret-handling contracts.
- Add synthetic candidate and job fixtures.
- Specify a minimal discovery-to-review vertical slice.

**Exit criteria:** schemas include provenance; private fields are identified; a persistence decision records trade-offs; fixtures contain no real personal data; the vertical slice has testable inputs, outputs, states, and exclusions.

## Discover & Rank — v0.2

**Outcome:** ingest jobs through one compliant path and produce useful, explainable recommendations.

- Specify the job-source adapter contract.
- Implement the first approved API, feed, or import adapter.
- Normalize job records and deduplicate them.
- Apply hard eligibility filters.
- Score remaining jobs with visible factors, evidence, and uncertainty.

**Exit criteria:** adapter terms and rate limits are documented; contract tests use synthetic fixtures; rankings are reproducible for fixed inputs; rejected jobs expose filter reasons.

## Tailored Materials — v0.3

**Outcome:** create application drafts without fabricating candidate claims.

- Build a verified evidence store.
- Validate generated claims against source evidence.
- Generate and export a tailored resume.
- Generate a source-grounded cover letter.

**Exit criteria:** every generated factual claim maps to evidence or is flagged; unsupported claims fail validation; exports pass deterministic structure tests; examples are synthetic.

## Apply & Track — v0.4

**Outcome:** support a review-first, resumable application workflow with auditable state.

- Implement application workflow states and events.
- Prototype one ATS adapter behind the review gate.
- Add idempotency and duplicate-submission protection.
- Define and expose an application-tracking dashboard contract.

**Exit criteria:** interrupted workflows resume safely; submission requires explicit approval by default; adapter tests cannot submit a real application; event history explains who or what changed state.

## Learn & Evaluate — v0.5

**Outcome:** use outcomes to make transparent, user-controlled recommendations.

- Capture application outcomes with explicit definitions.
- Create a privacy-safe offline evaluation dataset.
- Measure ranking and workflow quality.
- Propose ranking-weight adjustments for user approval.
- Complete a privacy and responsible-automation review.

**Exit criteria:** evaluation metrics and limitations are documented; recommendation evidence is visible; changes are never silently applied; deletion and export behavior are defined.

## Deliberately deferred

- Production scraping where access terms prohibit or restrict automation.
- Indiscriminate or high-volume automatic submission.
- Real-user credentials or personal data in hosted demos.
- Claims of universal ATS or job-board support.
- Cloud multi-tenancy, billing, and mobile applications.
- Incorporation of upstream material before license and provenance review.
