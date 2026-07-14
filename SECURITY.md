# Security policy

## Supported version

Security fixes target the latest tagged release and the default branch.

## Reporting

After the repository is published, report vulnerabilities through GitHub's private security advisory feature. Do not place credentials, private project files, device identifiers, or exploit details in a public issue.

## Scope

The bundled auditor is intended to be read-only. Reports that show project mutation, unsafe path traversal, credential exposure, implicit dependency installation, unapproved device mutation, or command execution are in scope.

The repository does not bundle Unity, Meta SDKs, `metavr`, ADB, or an MCP server. Vulnerabilities in those external products should also be reported to their maintainers.
