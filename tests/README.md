# Tests

The test suite will be organized by confidence boundary:

- unit tests for domain policies and pure transformations;
- contract tests for adapters using synthetic provider fixtures;
- integration tests for discovery-to-review workflows;
- end-to-end tests for synthetic scenarios without live submission;
- security tests for redaction, untrusted content, authorization, and idempotency.

Test commands will be added with the first executable package. Public tests must never require real candidate data or credentials.
