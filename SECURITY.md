# Repository security

Keep credentials, signing keys, local agent state, and plugin authentication data out of Git. Example environment files contain variable names and placeholders only. Ignoring a file does not remove an existing tracked copy or erase history.

Install the pre-commit framework and Gitleaks, then run `pre-commit install` in this repository. Before publishing, run `pre-commit run --all-files` and `gitleaks git --redact --log-opts="--all" .`. The pinned Go hook may require a Go toolchain on first install. Review hook updates before changing the pinned revision.

If a credential is committed, revoke or rotate it at the provider, remove it from tracking, and coordinate any history cleanup across branches, tags, clones and connected integrations. Do not disclose secret values in logs or tickets.
