# Estado operacional de segurança - 31/10/2026

Este arquivo é o checklist vivo da manutenção, não é certificado de pentest.

## Confirmado por evidência

- Produção Render em `757c7ec`: deploy `dep-dbj24b5g1s2s73fh56fg` **live** antes desta manutenção.
- CI no SHA `757c7ec`: 946 API, 103 scheduler e 14 web aprovados; frontend build passou.
- PR #100 da avaliação: cinco contratos de segurança adicionados, CI `41225462899` verde (951 API, 103 scheduler, 14 web). Incluídos na branch de manutenção.
- CSP atual restringe `script-src` a `self` no SPA, mas ainda permite `style-src 'unsafe-inline'`. Não remover sem testar todas as telas/legado.
- Supabase Security Advisor em 31/10: 10 tabelas internas com RLS habilitado sem policy; acesso direto é negado por padrão. NÃO criar policies de leitura para silenciar o linter.
- Performance Advisor: seis FKs sem índice de cobertura; medir planos de consulta e volume antes de DDL.
- Cliente Shopee Video isolado, bloqueado por `enabled` e autorização; OAuth/permissão oficial continuam pendentes.

## Riscos e próximos gates

| Tema | Situação | Próximo gate seguro |
| --- | --- | --- |
| Sincronismo Render | Staging falhou em `26d1e27`: build OK, **port scan timeout**; PR #101 sincroniza o código com main | Confirmar deploy staging **live**, verificar `/health`, `/api/health/ready` e logs |
| SBOM | Workflow novo | Gerar primeiro artefato, conferir CycloneDX e identificar diferenças Render |
| CSP | Estilos inline são dívida técnica atual | Migrar por tela, usar política report-only antes de enforcement; regressão visual em mobile/desktop |
| Rate limit distribuído | Em memória, um worker hoje | Redis/Key Value compartilhado, com testes de concorrência; obrigatório antes de escalar workers |
| Banco | RLS default-deny nas 10 internas | Verificar grants e exposição sem dar privilégio extra |
| Índices | Seis FKs sem cobertura | EXPLAIN / índice CONCURRENTLY após janela de mudança e backup |
| OAuth terceiros | End-to-end depende de autorização externa | Testar em conta autorizada, sem capturar credenciais reais |
| Segurança externa | Relatório técnico interno | Pentest independente, se exigido pela Shopee |
| Integração Shopee Video | Gateway preliminar, sem UI/OAuth, desabilitado | Aprovação de Shopee Video Management e teste de sandbox |

Documentos históricos de 17 e 20/10 descrevem um escopo anterior. Não reutilizar seus números como evidência de validação do commit atual.

## Referências

- `.github/workflows/ci.yml`, `.github/workflows/sbom.yml`
- `docs/RELATORIO-VALIDACAO-SEGURANCA-SHOPEE-2026-10-20.md`
- Vault: `Projetos/ShopeeAutoVendas/TASK.md`
- https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy
- https://supabase.com/docs/guides/database/database-linter?lint=0001_unindexed_foreign_keys

## Armazenamento de SBOM — intercorrência 31/10

O primeiro run `41226557115` gerou SBOM com Syft, porém o upload falhou por cota de GitHub Actions Artifacts esgotada. A estratégia foi alterada para escrever exclusivamente na branch `sbom-archive` (sem deploy), com proveniência SHA/branch. Marcar concluído apenas após execução e verificação de JSON no arquivo da branch.
