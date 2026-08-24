# Security Policy

## Supported versions

The project is in its foundation stage and has no production release. Security fixes will target the default branch until versioned releases begin.

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability or exposed secret. Use GitHub's **Security** tab to submit a private vulnerability report. Include:

- the affected component and revision;
- reproduction steps or a minimal proof of concept;
- potential impact, including privacy or duplicate-submission risk;
- any suggested mitigation;
- whether you believe credentials or personal data were exposed.

You should receive acknowledgement within seven days. Timelines for validation, remediation, and disclosure will depend on severity and project maturity. We will credit reporters who want attribution after coordinated disclosure.

## Security priorities

The project treats these as security-sensitive:

- candidate profiles, resumes, application answers, and outcomes;
- job-board, ATS, model-provider, and email credentials;
- prompt injection or malicious content in job postings;
- unsupported claims produced by a model;
- duplicate or unauthorized submission;
- unsafe logging, telemetry, exports, and fixtures;
- dependency, license, and provenance risk in external adapters.
