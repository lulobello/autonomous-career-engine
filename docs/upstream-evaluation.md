# Upstream Evaluation Policy

No third-party code, schema, fixture, prompt, model output, or documentation may be copied or adapted into this project until a maintainer records and approves an evaluation. Linking to or discussing a project as research does not by itself incorporate its material.

## Evaluation record

Create one document per proposed source under `docs/upstream/` with these sections:

1. **Identity:** repository or package name, canonical URL, owner, exact revision or version, and evaluation date.
2. **Proposed use:** exact files, concepts, interfaces, fixtures, or documentation being considered and why they are needed.
3. **License:** SPDX identifier, license file at the evaluated revision, compatibility with Apache-2.0, patent terms, copyleft conditions, and redistribution obligations.
4. **Attribution:** notices, copyright statements, source links, modification markers, and any documentation placement required.
5. **Provenance:** whether the source itself contains vendored, generated, or ambiguously licensed material.
6. **Security:** dependency risk, unsafe automation, credential handling, network behavior, data collection, and known advisories.
7. **Maintenance:** activity, release practices, test quality, and the cost of tracking upstream changes.
8. **Decision:** `approve`, `reject`, or `clean-room reimplement`, with rationale and an approving maintainer.

## Approval rules

- An absent, ambiguous, or incompatible license results in rejection or clean-room reimplementation.
- A license notice does not replace review of individual vendored files and dependencies.
- Clean-room work may use public behavior and documented interfaces, but must not translate or paraphrase protected implementation text.
- Approved incorporation must add required notices in the same pull request.
- The pull request must identify all derived files and preserve relevant history where practical.
- Security acceptance never implies license acceptance, and license acceptance never implies security acceptance.

## Current status

The foundation repository contains no incorporated upstream implementation. The README acknowledges ecosystem research separately and makes no claim of affiliation.
