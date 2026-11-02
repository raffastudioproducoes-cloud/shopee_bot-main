# Ajustes de posts — produto único, recorrência e rastreio (02/11/2026)

**Escopo:** branch de correção destinada exclusivamente a `staging`; produção/`main` não autorizadas. Contrato React + FastAPI + worker Flask. Não existe alteração de esquema SQL nem limpeza destrutiva de dados.

## Alterações implementadas no código

1. **Produto único:** o compositor usa seleção por rádio (Produtos ou Listas), permite retirar a seleção e substitui qualquer produto anterior ao selecionar outro. API recusa mais de um `product_id` em preview, batch, criação e atualização (HTTP 422), antes de escrever no banco. Posts antigos com múltiplos produtos continuam legíveis no modal.
2. **Fim do “Agendar”:** seletor de criação oferece somente **Agora** e **Recorrente**. O modo de data avulsa é rejeitado nas novas requisições `PostBatchCreate` sem `publish_immediately` e no endpoint legado `PostCreate`. O mecanismo interno de **Agora** continua usando o job de data com atraso de segurança de 5 minutos e disparo explícito; a coluna `trigger=date` e `run_date` da tabela `schedulers` precisam ficar para isso e para leituras históricas. **Não excluir colunas/tabelas nem registros antigos**: Supabase é compartilhado entre staging e produção.
3. **Horários em desktop:** controles separados de horas/minutos 24h, cinco atalhos, foco e teclado, sem o popup de AM/PM do Windows. Em dispositivos de ponteiro grosso (Android), permanece o `input type=time` nativo. Mantidos até cinco horários distintos por dia e validação tanto no cliente quanto na API.
4. **Status por ocorrência:** `GET /posts/{id}` devolve `schedule_slots[]`, com `day_of_week`, `time`, `status`, `last_at` e causa técnica `error` **só para ADMIN**. O worker registra `publish_jobs.idempotency_key` como `scheduler_id:YYYY-MM-DDTHH:MM` em horário de São Paulo; o backend cruza chave, dia, horário e scheduler. `succeeded` → *Postado*; `failed` → *Erro*; `pending` → *Programado*; `running` → *Em execução*; `unknown` → *Sem confirmação*. Sem job, exibe *Programado* (não afirma publicação). São consultados até 500 eventos recentes por post para encontrar o último por horário. Horários legados por data permanecem legíveis.
5. **Última postagem:** `last_published_at` vem da execução **confirmadamente** bem-sucedida na fila `publish_jobs` ou evento de sucesso legado em `activities`. Não confundir com `last_result.at` (última tentativa, que pode ter falhado). A tela de detalhes atualiza a consulta a cada 30 segundos enquanto aberta.
6. **Privacidade da falha:** resposta de API de cliente USER redige erros de publicação, sem URL, token, texto técnico ou informação diagnóstica; detalhes do modal mostram apenas título resumido do post e horário da falha. ADMIN mantém o diagnóstico técnico. A integração Threads extrai HTTP status, `error.code`, `error_subcode` e mensagem da Meta sem persistir a URL com parâmetros sensíveis.

## HTTP 403 do Threads — diagnóstico honesto

A captura fornecida mostra **403 ao chamar a criação de contêiner de mídia** (`POST /{threads-user-id}/threads`, `media_type=IMAGE`). A captura **não contém a resposta JSON da Meta** com `error.code` e `error_subcode`, então não permite afirmar a causa raiz. Possibilidades a verificar: token expirado ou revogado, falta de `threads_content_publish`/permissão do app, ID de usuário incompatível, restrição da conta, falha de acesso da Meta à mídia assinada. O OAuth atual já solicita `threads_basic,threads_content_publish` por padrão; **o consentimento de conexões antigas pode não incluir a concessão atual**.

Mudança segura: rejeição 4xx **na criação** do primeiro contêiner resulta em `failed` (não há chamada de publicação confirmada). Timeout, resposta ambígua na etapa `threads_publish` ou erro após partes já enviadas seguem como `unknown` e exigem reconciliação, **sem reenvio cego**. A correção de autorização depende de inspecionar o código Meta e, se necessário, reconectar a conta Threads; ela não pode ser declarada concluída sem testar a credencial real de staging. Não enviar posts de teste reais sem autorização do titular.

## Plano de verificação para homologação

- [ ] CI: suíte Python (Pydantic, API, worker) e build/typecheck frontend.
- [ ] Abrir modal de Novo post em desktop e Android; confirmar troca entre Produtos/Listas preservando no máximo um produto.
- [ ] Tentar payload de dois produtos nos endpoints de criação/preview/edição: obter 422 e nenhuma escrita.
- [ ] Conferir somente Agora/Recorrente; Agora ainda funciona via job interno e cron cria até cinco horários por dia.
- [ ] Desktop: teclado, mouse, seleção 00:00/23:59, duplicatas, remoção e atalhos; Android: native picker.
- [ ] Para um cron com segunda/quarta 18h, simular jobs por slot e confirmar que somente a segunda recebe etiqueta de erro.
- [ ] Verificar ADMIN vs USER com mesma falha e último sucesso anterior: somente ADMIN recebe diagnóstico, e “Última postagem” não muda para a tentativa falha.
- [ ] Obter **Meta error.code/subcode** do próximo 403 sem expor segredos; validar escopos da credencial de staging. Publicação real exige autorização explícita.
- [ ] Validar Render staging após CI/merge em staging. Não alterar main/produção.

## Limites e decisões

- Sem migração SQL: a tabela `schedulers` é usada também por Agora e por histórico, e o Supabase é comum à produção.
- Os slots exibem **última execução conhecida daquele dia/hora**, não todos os envios históricos; eventos antigos fora dos 500 mais recentes podem aparecer como “Programado”.
- Em caso de falha de leitura do histórico da fila, a UI não deve inventar uma postagem bem-sucedida.
- A resposta 403 específica não é “corrigida” sem seu código Meta e checagem de autorização real; código novo melhora diagnóstico, classificação e sigilo.

