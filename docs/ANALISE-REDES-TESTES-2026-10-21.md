# Testes de insights Meta - 2026-10-21

Escopo: leitura, sem publicar, alterar tokens ou expor segredos. Resultado: **ainda nao validado ponta a ponta**. "Pronto para teste" e preparacao do app, nao prova de consulta de insights nem aprovacao para usuarios comuns. A rota autenticada `POST /analytics/probe/{network}` usa o token do perfil ativo para uma consulta read-only e mostra apenas estado, HTTP e codigo de erro; sua resposta real ainda precisa ser observada no staging.

| Camada | Threads | Instagram | Facebook Pages |
| --- | --- | --- | --- |
| Permissao no rascunho Meta | `threads_manage_insights`, pronta para teste, 0 chamadas no print | `instagram_manage_insights`, pronta para teste, 0 chamadas | `read_insights`, pronta para teste, 0 chamadas |
| Conexao cadastrada no Supabase | 1 de 4 registros com `status=true`; teste real de identidade `ok` em 20/10 | 1 de 4; teste real de identidade `ok` em 20/10 | 1 de 4; teste real de identidade `ok` em 20/10 |
| Escopo no token conectado | Nao verificavel: a tabela nao grava escopos; novo OAuth passa a pedir `threads_manage_insights`, mas a conexao antiga nao recebe o escopo automaticamente | Nao verificavel: fluxo usa `INSTAGRAM_CONFIG_ID`; escopos dependem da configuracao Meta | Nao verificavel: fluxo usa `FACEBOOK_CONFIG_ID`; escopos dependem da configuracao Meta |
| Consulta de insights autenticada | Nao realizada | Nao realizada | Nao realizada |
| Resultado de metricas | Nenhum numero comprovado | Nenhum numero comprovado | Nenhum numero comprovado |

## Evidencia e limite

- Consulta read-only no projeto Supabase `wcentenooirmwwlwlljp`: `threads_credentials`, `instagram_credentials` e `facebook_credentials` tem quatro linhas cada e uma ativa cada. Nenhum valor de token foi selecionado. As linhas ativas foram atualizadas em 05/09/2026, antes de as permissoes de insights entrarem no rascunho em 21/10/2026; os testes de identidade em `credential_checks` ficaram `ok` em 20/10. Portanto as credenciais existem e o backend consegue usa-las para o teste atual, mas esse teste nao exige a permissao de insights. `posts` tem seis linhas (duas por rede); `publish_jobs` tem zero linhas. O esquema de `posts` nao guarda ID externo da publicacao. Isso impede correlacionar esses registros legados a insights de post sem consultar a API do titular.
- O conector Meta confirma as tres permissoes no rascunho, mas `can_submit=false` porque ha envio anterior em analise. Para as tres, ainda marca caso de uso, gravacao, API precheck e data-use como incompletos. O conector tambem traz estado de privilegio divergente da interface; por isso o portal e uma resposta autenticada da API devem prevalecer para comprovar acesso.
- O navegador autenticado perdeu o acesso de automacao ao abrir o Graph API Explorer. Uma tentativa de shell seguro no Render retornou `Permission denied (publickey)`. O conector Render oferece leitura de servico/logs, mas nao shell ou leitura de variaveis de ambiente. Nenhuma chamada autenticada a Graph API ou Threads API foi efetuada. Nao atribuir esse limite a bloqueio de permissao da plataforma nem afirmar que as credenciais estao ausentes.
- Nenhum post foi criado, alterado ou excluido neste teste.
- Commit `2f091f7` entrou em `staging` e o deploy Render `dep-dbckcus9v7es73bl80m0` ficou `live` em 21/10/2026. `POST /api/analytics/probe/threads` sem sessao retornou HTTP 401, confirmando a barreira de autenticacao. Isso nao exercita o token do usuario. A automacao da aba Chrome autenticada continuou com `Debugger unattached`; a extensao visivel no print e ChatGPT, nao ha uma extensao Codex a instalar. Testes locais especificos: 12 passaram; build do frontend passou. Suíte API: 853 passaram e 3 falharam porque o ambiente virtual local tem PyJWT, `python-multipart` e Pillow em versoes diferentes das exigidas pelos testes de seguranca. Nenhum desses resultados autoriza dizer que a consulta real de insights funcionou.

## Para concluir o teste real

1. Confirmar no Meta Business Login as permissoes solicitadas pelos `FACEBOOK_CONFIG_ID` e `INSTAGRAM_CONFIG_ID`. Em Threads, adicionar `threads_manage_insights` ao consentimento antes de reconectar a conta de teste; nao forcar reconexao de usuarios comuns antes da aprovacao.
2. Reautorizar voluntariamente as tres contas de teste e conferir os escopos efetivos com o depurador/endpoint oficial, sem registrar tokens no relatorio ou em logs.
3. Obter pelo menos um ID proprio de post ou perfil e fazer GET autenticado de insights de cada rede, anotando somente HTTP status, nomes de metricas, data e tipo de midia. Confirmar isolamento entre dois perfis antes de expor os numeros no site.
4. Aguardar App Review/publicacao para usuarios sem papel no app. Uma consulta bem-sucedida com a conta ADMIN nao comprova acesso desses usuarios.

Referencias oficiais: [Threads Insights](https://developers.facebook.com/docs/threads/insights/), [Threads Get Started](https://developers.facebook.com/docs/threads/get-started/), [Meta App Review](https://developers.facebook.com/apps/1804230767234146/app-review/submissions/).
