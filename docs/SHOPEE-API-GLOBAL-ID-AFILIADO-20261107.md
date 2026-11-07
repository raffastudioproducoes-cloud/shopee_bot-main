# Shopee Afiliados — API global com identificação individual

**Data:** 07/11/2026 · **Estado:** migration 090 aplicada; código em preparação para homologação em `staging`, **nunca** promoção automática a `main` · **Versão candidata:** MINOR `3.5.0` (arquivo `VERSION` fica `3.4.0` até release autorizada).

## Decisão de produto

1. A plataforma Auto Orbital fornece e administra **uma credencial App ID/Secret Shopee** para consultas de produtos. Somente ADMIN a vê/configura/testa no painel `/admin/credentials`. O backend mantém o segredo cifrado no Supabase e jamais o devolve em JSON.
2. Cada **conta** USER/ADMIN fornece apenas seu **ID numérico de afiliado Shopee** (ou link **expandido** da Shopee contendo `affiliate_id` ou `utm_source=an_<ID>`). O ID fica na conta e é compartilhado por seus perfis, sem OAuth e sem acesso à conta Shopee do cliente.
3. A busca usa a App ID/Secret global; o link de cada produto é **reconstruído no servidor** pela URL original oficial e o ID da conta. Nenhum `offerLink` emitido para a credencial do dono é devolvido ao usuário.
4. Falta de ID bloqueia novas buscas com aviso para cadastrar ID. Falta de chave global bloqueia catálogo com aviso neutro e sem segredo. **Não usar o ID do ADMIN como fallback.**

## Evidência e ressalva comercial

- [Guia oficial da Shopee de links `an_redir`](https://help.shopee.sg/portal/10/article/171184-Affiliate-Short-Link-Implementation-Guide): demonstra `origin_link` URL-encoded + `affiliate_id` e redirecionamento final `utm_source=an_<ID>`; `sub_id` é rastreio auxiliar, não substitui o beneficiário.
- [Shopee Brasil — cadastro e ID de afiliado](https://help.shopee.com.br/portal/10/article/127648-Conhe%C3%A7a-a-Plataforma-de-Criadores-e-Afiliados-da-Shopee) e [geração de links oficiais](https://help.shopee.com.br/portal/10/article/128461-Passo-a-Passo-para-Gerar-Seus-Links-de-Afiliado).
- [Termos do programa no Brasil](https://help.shopee.com.br/portal/10/article/124094): atribuição e pagamento sujeitos às regras vigentes, elegibilidade e último clique.
- A documentação pública detalhada de `an_redir` encontrada é de outras regiões Shopee; **não representa aprovação formal de uso via App ID única para clientes brasileiros**. O site concorrente demonstrado por Rafa é evidência funcional externa, não uma garantia contratual. **Homologação real ainda necessária:** usuário e ADMIN conferirem o destino com `utm_source=an_ID` correspondente ao afiliado, registro de clique/conversão na Shopee e regras de uso comercial da API. Não declarar comissão paga apenas pela aparência da URL.

## Contrato técnico

| Camada | Responsabilidade | Controle |
| --- | --- | --- |
| Supabase `platform_shopee_credentials` | App ID e segredo Fernet por `environment=staging/production`; cópia cifrada da última chave ativa ADMIN na migração 090 | RLS, `REVOKE` de `anon/authenticated`, `service_role` apenas |
| Supabase `shopee_affiliate_accounts` | Par `(user_id, affiliate_id)` único por conta | RLS restritiva; API exige JWT e `scope_account`; não aceita credenciais do cliente |
| `GET/PUT/DELETE /shopee/affiliate` | Status, cadastrar/remover ID do próprio usuário | Validação numérica de 5–20 dígitos ou URL expandida autorizada |
| `GET/PUT/DELETE /admin/shopee` + `POST /admin/shopee/test` | Gestão e teste da API central | ADMIN obrigatório; não devolve segredo; teste usa bridge existente |
| `/products/catalog-search` | API global retorna produtos; resposta mapeada com `an_redir` por conta | `offerLink` do dono nunca é publicado; limite atual de busca mantido |
| Produtos/listas salvos | Reescrever links Shopee **na resposta** e **ao inserir produto novo** | Impede exposição de links antigos salvos; nenhuma migração destrutiva dos produtos |
| `POST /posts/generate-copy` | Substituir link antigo do produto antes de criar prompts de IA | Nunca inserir link de comissão da conta ADMIN no texto gerado para outro afiliado; exige ID em produto Shopee |
| Novos rascunhos de campanha | Fixar URL original e link individual no snapshot | Preflight/ativação rejeita snapshot novo com ID alterado; jobs existentes NÃO reescritos |

**URL emitida:** `https://s.shopee.com.br/an_redir?origin_link=<url_original_https_shopee_com_br_codificada>&affiliate_id=<id_da_conta>`.

**Limites claros:** links curtos opacos não permitem inferir ID sem expandi-los, portanto são recusados sem fazer requisição de rede (proteção SSRF). O ID informado não comprova propriedade do cadastro; autenticação forte da conta Shopee exigiria um fluxo OAuth oficial específico. Produtos externos/URLs não oficiais seguem regras legadas. Rascunhos históricos sem origem verificável e publicações agendadas anteriormente não são reescritos silenciosamente. Textos livres escritos manualmente pelo usuário não sofrem substituição automática.

## Migração e rollback

1. Verificar projeto Supabase correto, schema de `users`/`shopee_credentials`, migração 089, `pg_cron`, Render e branch.
2. Executar `090_platform_shopee_affiliate_ids.sql` **aditiva e idempotente**, registrar exatamente uma linha em `public.migrations`, inspecionar somente presença de chaves cifradas sem recuperar seus valores. A mesma base atende staging e produção, e a `main` antiga ignora as tabelas novas.
3. Rodar CI Python 3.13, frontend Node 20, teste PostgreSQL 16 descartável com RLS e smoke real do Render antes de declarar `staging` LIVE. Confirmar que os dois cron SQL existentes não foram alterados.
4. Homologar com pelo menos duas contas de afiliado e verificar separação entre URLs, perfil, ausência de vazamento e redirecionamento Shopee. Somente Rafa autoriza release SemVer e PR `staging → main`.
5. **Rollback de código:** manter `main` em 3.4.0. Não excluir as tabelas nem chaves históricas se for necessário revertê-lo. A chave legado segue cifrada para compatibilidade, mas **não** é usada no catálogo novo.

## Estado de validação

- Implementação, contratos API, frontend, migration e CI elaborados na branch `feat/shopee-affiliate-id-shared-catalog-20261107` a partir de `origin/staging`.
- Teste API local: 1.265 PASS (07/11, Python 3.12), com teste posterior extra de ADMIN testando API global (8/8 focados). Scheduler 208 PASS/1 XFAIL, web 27 PASS, build Vite/TypeScript PASS, seis testes Node da tela PASS, lint bloqueante 0. Incluídos testes de isolamento 090 e PostgreSQL 16 em CI.
- **Supabase aplicado e verificado em 07/11/2026** (projeto `wcentenooirmwwlwlljp`): migration 090 executada com sucesso pelo conector e registrada uma vez em `public.migrations` (`id=85`). Ambas as configurações `production` e `staging` têm metadados de App ID e segredo cifrado presentes, sem consultar seus valores; `shopee_affiliate_accounts` ainda tem zero IDs. RLS habilitada nas duas tabelas, SELECT público anônimo/autenticado negado. `pg_cron` segue exatamente com `auto-orbital-wake-v1` (`*/2`) e `auto-orbital-uptime-sample-v1` (`*/12`), sem escrita em cron ou `pg_net`.
- **Ainda não comprova:** CI remota, login ADMIN e USER no staging, Shopee GraphQL ao vivo ou atribuição de comissões. Registrar resultados após cada gate; não confundir testes simulados com pagamento real.
- **GitHub Actions:** disponível novamente em 07/11 (bloqueio de franquia encerrado). Esta tarefa deve usar CI; se houver indisponibilidade posterior, manter em branch e registrar incidente antes de qualquer merge.
