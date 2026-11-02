# Incidente: falha ao criar post recorrente no Threads — HTTP 503 (02/11/2026)

**Ambiente:** somente staging. **Estado:** causa confirmada e tratamento preventivo implementado; o agendador deste ambiente permanece desativado até haver execução isolada/autorizada. **Produção e `main`:** sem alterações.

## 1. Sintoma reportado

No modal de **Novo post**, o usuário configurou um produto da Shopee, uma foto importada, descrição válida para Threads (290/500 caracteres), recorrência nos sete dias da semana e cinco horários Brasília (09:00, 12:00, 15:00, 18:00, 21:00). A interface mostrou:

> Threads: falhou — Não foi possível agendar esta rede agora.

Os controles de texto e mídia indicaram conteúdo compatível; a falha não veio do limite de caracteres nem da plataforma Threads.

## 2. Rastreamento e causa raiz

Evidências **somente leitura**, sem consultas destrutivas e sem publicações reais:

1. Render `shopee-bot-staging` às **2026-11-02 04:43:16–04:43:20 UTC**: a importação da foto Shopee retornou HTTP 201; a prévia de post HTTP 200; `POST /posts/batch` retornou HTTP 201 com resultado **bloqueado** para Threads.
2. Log interno do backend às **04:43:18.906 UTC**: `Falha ao registrar agenda: func=bot_post ... jobs_criados=0 tipo=InternalApiError detalhe=create_scheduler_job falhou: HTTP 503`. O rollback do plano foi acionado; a primeira agenda nem chegou a ser criada.
3. Em `web/routes/internal.py`, o decorator `_require_scheduler_role` devolve HTTP 503 quando `scheduler_enabled()` é falso; a função lê `SCHEDULER_ENABLED` no processo Flask. O último log de inicialização do scheduler de staging foi em **30/10/2026 21:39 UTC**, apesar de vários deploys depois. A causa observável é a instância de staging **sem execução do agendador**.
4. A instância Render de **produção** tem registros de `Scheduler initializing...` até 01/11/2026; ambas as instâncias usam o Supabase compartilhado. Por isso, simplesmente ligar o scheduler de staging pode fazer duas instâncias carregarem os mesmos jobs, com risco de disputas e publicações indevidas, mesmo com leases de publicação. **Não ligar a flag por este ajuste.**
5. A API de lote tratava o erro interno como bloqueio individual dentro de um HTTP 201. O frontend desconhecia a indisponibilidade e só informava genericamente a falha **depois** de criar rascunho de mídia e tentar criar o post.

A hipótese de origem exata da configuração da variável no Render (quem alterou/quando) não foi auditada; a condição operacional de desativação, o retorno 503 e o código do guard estão confirmados.

## 3. Correção implementada (sem reativar publicação)

- **Flask / scheduler:** `scheduler_ready()` confirma flag habilitada, worker inicializado, running e sem shutdown. `GET /internal/scheduler/status` só atende com `X-Internal-Secret` válido e não cria/dispara jobs.
- **Ponte interna FastAPI:** `scheduler_availability()` consulta esse endpoint com timeout, valida booleano e falha de forma segura em 403, 5xx, timeout ou resposta inválida. O corpo interno nunca é enviado ao browser.
- **API pública autenticada:** `GET /posts/scheduler-status` devolve disponibilidade e aviso simples. `POST /posts/batch` e a rota legada fazem **preflight antes de qualquer escrita de posts, vínculo de mídia ou job**. Em indisponibilidade, devolvem HTTP **503 explícito**, sem criar postagem parcial e com mensagem de rascunho preservado. A prévia e a geração de texto continuam disponíveis.
- **Frontend:** consulta status ao abrir criação, atualiza periodicamente, mostra aviso sob **Quando publicar?** e desabilita **Criar** enquanto o serviço não estiver disponível. Ao tentar enviar, confere novamente **antes de upload de imagens/vídeos**, prevenindo uploads inúteis. O backend repete a checagem por segurança contra mudanças de estado.
- **Persistência:** campos preenchidos (incluindo as remoções intencionais) seguem no rascunho local por conta/perfil. Falha não limpa o rascunho nem reenvia publicação. Não altera scheduler global ou banco compartilhado.

## 4. Testes sem efeitos externos

| Caso | Verificação |
|---|---|
| Worker desabilitado | Endpoint interno privado informa `available=false` |
| Sem segredo interno | Status privado retorna 403 |
| Ponte interna | Lê `false` e recusa resposta que não seja booleano |
| Criação de lote com scheduler inativo | Retorna HTTP 503 **antes** de consultar mídia ou chamar `_create_thread` |
| Status público | Exibe aviso genérico sem detalhes internos |
| Frontend | Verifica status antes de uploads e botão desabilitado quando indisponível |
| Regressão existente | Todos os testes de rotas, recorrências, mídia, publicação e build seguem executados no CI |

Não há teste que cria publicação real no Threads, insere job ou altera Supabase.

## 5. Limitação operacional e próxima decisão

Esta correção elimina a falha tardia e evita o efeito colateral de uploads/agendas parciais, **mas não liga o scheduler**. Enquanto `SCHEDULER_ENABLED` estiver desativado, o staging mostrará explicitamente que não pode criar post recorrente/Agora. A solução de execução real exigirá isolar jobstore e escopo de execução por ambiente (ou separar banco/worker de staging), homologar deduplicação e obter autorização para agendamentos reais de teste. **Não desativar/verificar a proteção atual por tentativa e erro.**

## 6. Implantação e documentação

Branch destinada à `staging` via PR/CI; guia mestre, `docs/TASK.md` e Vault devem mencionar tanto a causa quanto a limitação. A `main` e o site de produção permanecem intocados.
