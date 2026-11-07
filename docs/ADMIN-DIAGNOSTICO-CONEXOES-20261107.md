# Diagnóstico ADMIN: cartões compactos e verificação consolidada

Data: 07/11/2026 · Estado: **branch de homologação → staging** · Versão oficial: `3.4.0` · Candidata funcional: `3.5.0` (MINOR compatível).

## Pedido e comportamento

- Rota **`/admin/credentials`** apenas para ADMIN. Os painéis **Inteligência Artificial** e **Shopee Afiliados** aparecem em ordem alfabética, lado a lado no desktop e empilhados em telas estreitas. Ambos iniciam fechados e expandem pelo cabeçalho acessível; carregam logos locais reais e informam o estado sem abrir o formulário.
- Ao expandir, a gestão de **provedor de IA, chave, modelo, ativação, desconexão** e de **Shopee App ID/Secret, atualização, desconexão** permanece. Os valores secretos nunca são reexibidos. Saem os botões individuais de testar.
- A seção inferior **Estado das conexões** mostra Facebook, Instagram, Kwai, Threads, TikTok e X, com logo local, nome, estado real e último teste. **Não existem mais campos de override social na página.** Rotas e credenciais legadas de override ADMIN são preservadas no backend, apenas sem formulário nesta interface (compatibilidade, sem exclusão dos dados).
- **Um único botão** “Testar todas as conexões” executa `POST /admin/credentials/test-all`, bloqueado durante a requisição. Exibe contagens, resultado por rede e atualiza IA/Shopee/status das redes.

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
- Browser: revisão visual em ADMIN autenticado da **staging** ocorre após deploy do código. Testes automatizados e health HTTP não equivalem a validação visual da tela.
- Ações externas e logs reais só devem ser declarados confirmados após executar o botão autenticado na **staging** e observar `request_logs`/Render, sem colar credenciais no chat.

## Versionamento e promoção

- `VERSION=3.4.0` preservada. Inserir alteração em `[Não lançado]`; manter MINOR candidata `3.5.0` para a release após homologação.
- Tarefa: desenvolvimento em `feat/admin-diagnostico-compacto-20261107`, PR e CI para `staging`, Render LIVE e smoke; **nenhum PR ou merge de `main` sem aprovação posterior**.
