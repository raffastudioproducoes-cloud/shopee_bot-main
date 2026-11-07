# Diagnóstico ADMIN: cartões compactos e verificação consolidada

Data: 07/11/2026 · Estado: **staging LIVE e QA visual autenticado concluído** · Versão oficial: `3.4.0` · Candidata funcional: `3.5.0` (MINOR compatível).

## Implantação verificada (07/11/2026)

- [PR #322](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/322) aprovada pela [CI #1067](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42363907682), três jobs `success`: API Python/lint, Frontend TypeScript/build/Node e PostgreSQL descartável. O job `Staging externo` da PR ficou `skipped` por configuração do workflow; a checagem real foi feita após o deploy.
- Merge **somente `staging`** `8345cc74c2ba31f58e70fd0a074ef77485aa5f2b`; Render `dep-dbnfq30473hc739jbs30` **LIVE**, mesmo commit.
- Smoke remoto: [`/health`](https://shopee-bot-staging.onrender.com/health) e [`/api/health/ready`](https://shopee-bot-staging.onrender.com/api/health/ready) responderam `{"status":"ok"}`.
- Browser ADMIN autenticado em [`/admin/credentials`](https://shopee-bot-staging.onrender.com/admin/credentials): verificados os dois cards globais na mesma linha, logos carregadas, resumo de status, expansão/recolhimento independente, campos globais preservados, seis status sociais compactos e botão único habilitado. Não foram inseridos nem revelados tokens.
- **Pendente de homologação funcional externa:** o botão consolidado não foi acionado com as credenciais reais nesta sessão; portanto, não se afirma que houve novas chamadas pagas a provedores nem novos eventos reais do lote no banco/Render. O contrato e a auditoria foram cobertos por testes automatizados. Layout mobile validado por CSS e build, sem captura visual real de viewport móvel.
- `main` e produção não foram alteradas; Rafa decidirá a promoção depois da homologação.

## Pedido e comportamento

- Rota **`/admin/credentials`** apenas para ADMIN. Os painéis **Inteligência Artificial** e **Shopee Afiliados** aparecem em ordem alfabética, lado a lado no desktop e empilhados em telas estreitas. Ambos iniciam fechados e expandem pelo cabeçalho acessível; carregam logos locais reais e informam o estado sem abrir o formulário.
- Ao expandir, a gestão de **provedor de IA, chave, modelo, ativação, desconexão** e de **Shopee App ID/Secret, atualização, desconexão** permanece. Os valores secretos nunca são reexibidos. Saem os botões individuais de testar.
- A seção inferior **Estado das conexões** mostra Facebook, Instagram, Kwai, Threads, TikTok e X, com logo local, nome, estado real e último teste. **Não existem mais campos de override social na página.** Rotas e credenciais legadas de override ADMIN são preservadas no backend, apenas sem formulário nesta interface (compatibilidade, sem exclusão dos dados).
- **Um único botão** “Testar todas as conexões” executa `POST /admin/credentials/test-all`, bloqueado durante a requisição. Exibe contagens, resultado por rede e atualiza IA/Shopee/status das redes.

### Extensão do catálogo visual — 07/11/2026 (staging)

- Mantidos os dois painéis globais superiores de **IA** e **Shopee**; a API Shopee global já representa a loja Shopee, sem criar uma segunda credencial fictícia.
- Em **Estado das conexões**, adicionadas seções distintas **Lojas** e **Redes sociais**, mantendo cards compactos, logos e ordem alfabética PT-BR dentro de cada seção.
- **12 lojas planejadas:** AliExpress, Amazon, Americanas, Magazine Luiza, Mercado Livre, Natura e Avon, Pró Spin, Rede Awin, Rede Lomadee, Rede Rakuten, SHEIN e TerabyteShop.
- **9 canais sociais:** Facebook, Instagram, Kwai, Shopee Vídeo, Telegram, Threads, TikTok, WhatsApp e X. Os três novos cards informativos são Shopee Vídeo, Telegram e WhatsApp.
- O catálogo do ADMIN usa `buildAdminDiagnosticSections()` e `FUTURE_CREDENTIAL_PLATFORMS` já compartilhado com a página comum; novos placeholders catalogados passam a aparecer no ADMIN automaticamente.
- Plataformas ainda não implantadas exibem **"Em breve"**: sem indicadores fictícios de conexão, sem formulários e sem testes ou chamadas de API. O botão existente continua limitado às **oito integrações reais já previstas** (IA, Shopee global e seis sociais). Nenhuma mudança de contrato backend, credencial salva, migrations, `pg_cron` ou `pg_net`.
- Suíte Node de catálogo verifica as 21 entradas abaixo dos painéis globais (12 lojas + 9 sociais), agrupamento, ordem e disponibilidade. QA visual deve ser repetido após o novo deploy. Estado: **aguardando CI e Render da atualização visual**, promoção a `main` continua proibida sem autorização.

## Contrato do teste

`POST /admin/credentials/test-all` exige sessão **ADMIN** (dependência de rota) e perfil atual. Conta uma tentativa no rate limit existente (`6/min` por ADMIN). A ação valida, com concorrência máxima 3:

1. Somente a **IA ativa da plataforma** quando há chave salva (Gemini/OpenAI/Anthropic conforme seleção).
2. Somente **Shopee Afiliados global** quando há App ID/Secret, **não** o ID de afiliado individual.
3. Somente credenciais sociais **do perfil ADMIN autenticado** que realmente estejam conectadas, nos seis provedores suportados. Nunca busca tokens de clientes ou outros perfis.

Cada entrada retorna `{state: 'ok'|'error'|'skipped', status_text, checked_at}`; `skipped` significa **sem conexão configurada**, não falha nem teste simulado. Os validadores atuais atualizam `credential_checks` e estados globais na base já existente. Falhas isoladas de serviço ou timeout não cancelam os demais resultados. Exceções/erros internos são devolvidos com rótulos genéricos, sem mensagem crua de fornecedor, cabeçalhos, tokens ou IDs.

**Auditoria:** cada teste executado gera `logger.info` no Render com o identificador público da rede e estado genérico. Também solicita gravação em `request_logs` por `log_action(..., force=True)` apenas para eventos enumerados `admin_credentials_test_{rede}_{ok|error}` e `admin_credentials_test_all`, com usuário ADMIN e resultado seguro. É exceção **estritamente focada** ao flag de logging geral, não o liga nem coleta outras rotas. O endpoint continua devolvendo resultados mesmo que a gravação do log falhe (falha best effort, registrada no servidor); a Central de Logs identifica esses eventos por rótulos fixos. Não cria schema nem nova tabela.

**Não comprova:** autorização real de publicação, remuneração Shopee, login OAuth em contas de clientes ou entrega de mensagem/post. Só comprova que os validadores de conexão configurados responderam na execução do teste.

## Segurança, compatibilidade e operação

- Mantidos: autenticação ADMIN, criptografia Fernet, segredo no servidor, RLS/camadas de ownership, perfis e credenciais já salvas, rate limit, método de consulta aos fornecedores e logs sanitizados.
- Nenhum DDL, migration, atualização de token real por edição administrativa, alteração de scheduler/cron/pg_net/filas, billing, OAuth, ou publicação externa.
- Semântica de `staging`: somente branch de teste homologada; **main permanece protegida até nova aprovação de Rafa**. Supabase é único e compartilhado; os dois jobs `pg_cron` ficam intocados.
- Identidade visual: logos existentes de `/brand-logos` para Shopee e seis redes; `gemini.svg` do [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Google_Gemini_icon_2025.svg), arte de Google LLC. Uso nominativo, sem alegar parceria.

## QA e evidências

- API: novos testes `tests/api/test_admin_credential_batch.py` cobrem autorização, limite único, seis redes sem ligação, IA/Shopee globais, erro de uma rede sem interromper lote, ausência de segredo no payload/log e falta de configuração. `tests/api/test_admin_privacy.py` cobre rótulos permitidos dos eventos.
- `tests/api/test_profile_scope_logs_audit.py` comprova a exceção auditável `force=True` com logging global desligado. **1.271/1.271** testes em `tests/api` passaram localmente em 07/11/2026.
- Frontend: `admin-diagnostics-compact.test.mjs`, contratos atualizados para o botão único, manutenção do CRUD global e remoção visual de override; `npm run build` verifica TypeScript/CSS/Vite.
- Browser: revisão visual autenticada na **staging LIVE** realizada (desktop, cards fechados/abertos e estado real consultado). Teste externo do botão e inspeção do log resultante permanecem para homologação funcional.
- Ações externas e logs reais só devem ser declarados confirmados após executar o botão autenticado na **staging** e observar `request_logs`/Render, sem colar credenciais no chat.

## Versionamento e promoção

- `VERSION=3.4.0` preservada. Inserir alteração em `[Não lançado]`; manter MINOR candidata `3.5.0` para a release após homologação.
- Tarefa: desenvolvimento em `feat/admin-diagnostico-compacto-20261107`, PR e CI para `staging`, Render LIVE e smoke; **nenhum PR ou merge de `main` sem aprovação posterior**.
