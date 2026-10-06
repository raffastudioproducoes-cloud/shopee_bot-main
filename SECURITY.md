# Repository security

Keep credentials, signing keys, local agent state, and plugin authentication data out of Git. Example environment files contain variable names and placeholders only. Ignoring a file does not remove an existing tracked copy or erase history.

Install the pre-commit framework and Gitleaks, then run `pre-commit install` in this repository. Before publishing, run `pre-commit run --all-files` and `gitleaks git --redact --log-opts="--all" .`. The pinned Go hook may require a Go toolchain on first install. Review hook updates before changing the pinned revision.

If a credential is committed, revoke or rotate it at the provider, remove it from tracking, and coordinate any history cleanup across branches, tags, clones and connected integrations. Do not disclose secret values in logs or tickets.

## Reportar uma vulnerabilidade

Envie o relato por e-mail para **contato.raffasp@gmail.com**, com o assunto "Segurança". Não abra issue
pública nem publique detalhes antes de o problema ser corrigido.

Inclua, se possível: o que foi encontrado, onde (rota, tela ou arquivo), passos para reproduzir e o
impacto que você enxerga. Não inclua credenciais, tokens ou dados reais de terceiros no relato; se
precisar provar o acesso, descreva-o sem anexar o segredo.

Este é um projeto proprietário mantido por uma pessoa: não há prazo de resposta garantido nem
programa de recompensa. Relatos feitos de boa-fé, sem acesso a dados de outros usuários além do
necessário para demonstrar o problema, serão tratados com prioridade.

Versões suportadas: apenas a que está em `main` (ver `VERSION`).
