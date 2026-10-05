# Security

This project runs experiment modules as Python code. Treat an experiment from a pull
request as untrusted until reviewed.

Report vulnerabilities, including ways to make the verifier accept a corrupted result,
through GitHub's private vulnerability reporting for this repository (Security tab).
Please do not open a public issue for them. Ways to fool the checks that are not
security-sensitive can use the "Verifier blind spot" issue form.

The checks are not a sandbox and do not protect against someone who controls the
repository history. See section 9 of `PROTOCOL.md`.
