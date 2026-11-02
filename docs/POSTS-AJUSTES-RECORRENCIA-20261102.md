# Ajustes de posts — produto único, recorrência e rastreio (02/11/2026)

**Escopo:** branch de correção destinada exclusivamente a `staging`; produção/`main` não autorizadas. Contrato React + FastAPI + worker Flask. Não existe alteração de esquema SQL nem limpeza destrutiva de dados.

## Alterações implementadas no código

1. **Produto único:** o compositor usa seleção por rádio (Produtos ou Listas), permite retirar a seleção e substitui qualquer produto anterior ao selecionar outro. API recusa mais de um `product_id` em preview, batch, criação e atualização (HTTP 422), antes de escrever no banco. Posts antigos com múltiplos produtos continuam legíveis no modal.
2. **Fim do “Agendar”:** seletor de criação oferece somente **Agora** e **Recorrente**. O modo de data avulsa é rejeitado nas novas requisições `PostBatchCreate` sem `publish_immediately` e no endpoint legado `PostCreate`. O mecanismo interno de **Agora** continua usando o job de data com atraso de segurança de 5 minutos e disparo explícito; a coluna `trigger=date` e `run_date` da tabela `schedulers` precisam ficar para isso e para leituras históricas. **Não excluir colunas/tabelas nem registros antigos**: Supabase é compartilhado entre staging e produção.
3. **Horários em desktop:** controles separados de horas/minutos 24h, cinco atalhos, foco e teclado, sem o popup de AM/PM do Windows. Em dispositivos de ponteiro grosso (Android), permanece o `input type=time` nativo. Mantidos até cinco horários distintos por dia e validação tanto no cliente quanto na API.
4. **Status por ocorrência:** `GET /posts/{id}` devolve `schedule_slots[]`, com `day_of_week`, `time`, `status`, `last_at` e causa técnica `error` **só para ADMIN**. O worker registra `publish_jobs.idempotency_key` como `scheduler_id:YYYY-MM-DDTHH:MM` em horário de São Paulo; o backend cruza chave, dia, horário e scheduler. `succeeded` → *Postado*; `failed` → *Erro*; `pending` → *Programado*; `running` → *Em execução*; `unknown` → *Sem confirmação*, ou *Erro parcial* quando um HTTP 4xx bloqueou uma parte posterior e o evento confirma que ao menos uma parte já havia sido enviada. A fila continua `unknown` nesses casos para impedir reenvio automático. Sem job, exibe *Programado* (não afirma publicação). São consultados até 500 eventos recentes por post para encontrar o último por horário. Horários legados por data permanecem legíveis.
5. **Última postagem:** `last_published_at` vem da execução **confirmadamente** bem-sucedida na fila `publish_jobs` ou evento de sucesso legado em `activities`. Não confundir com `last_result.at` (última tentativa, que pode ter falhado). A tela de detalhes atualiza a consulta a cada 30 segundos enquanto aberta; a lista também reconsulta recorrências ativas a cada 30 segundos, inclusive quando a última tentativa falhou, para atualizar a última postagem confirmada.
6. **Privacidade da falha:** resposta de API de cliente USER redige erros de publicação, sem URL, token, texto técnico ou informação diagnóstica; detalhes do modal mostram apenas título resumido do post e horário da falha. ADMIN mantém o diagnóstico técnico. A integração Threads extrai HTTP status, `error.code`, `error_subcode` e mensagem da Meta sem persistir a URL com parâmetros sensíveis.

## HTTP 403 do Threads — diagnóstico honesto

A captura fornecida mostra **403 ao chamar a criação de contêiner de mídia** (`POST /{threads-user-id}/threads`, `media_type=IMAGE`). A captura **não contém a resposta JSON da Meta** com `error.code` e `error_subcode`, então não permite afirmar a causa raiz. Possibilidades a verificar: token expirado ou revogado, falta de `threads_content_publish`/permissão do app, ID de usuário incompatível, restrição da conta, falha de acesso da Meta à mídia assinada. O OAuth atual já solicita `threads_basic,threads_content_publish` por padrão; **o consentimento de conexões antigas pode não incluir a concessão atual**.

Mudança segura: rejeição 4xx **na criação** do primeiro contêiner resulta em `failed` (não há chamada de publicação confirmada). Timeout, resposta ambígua na etapa `threads_publish` ou erro após partes já enviadas seguem como `unknown` e exigem reconciliação, **sem reenvio cego**. A correção de autorização depende de inspecionar o código Meta e, se necessário, reconectar a conta Threads; ela não pode ser declarada concluída sem testar a credencial real de staging. Não enviar posts de teste reais sem autorização do titular.

## Plano de verificação para homologação

- [x] CI: suíte Python, build/typecheck e testes frontend passaram nos PRs #181 e #182; novo PR de falha parcial depende de CI adicional.
- [x] Modal em Chrome desktop: seleção única validada ao trocar produto; Android ainda pendente.
- [ ] Tentar payload de dois produtos nos endpoints de criação/preview/edição: obter 422 e nenhuma escrita.
- [x] Interface Chrome mostra somente Agora/Recorrente; publicação real Agora e cron não executadas nesta validação.
- [ ] Desktop: teclado, mouse, seleção 00:00/23:59, duplicatas, remoção e atalhos; Android: native picker.
- [ ] Para um cron com segunda/quarta 18h, simular jobs por slot e confirmar que somente a segunda recebe etiqueta de erro.
- [ ] Verificar ADMIN vs USER com mesma falha e último sucesso anterior: somente ADMIN recebe diagnóstico, e “Última postagem” não muda para a tentativa falha.
- [ ] Obter **Meta error.code/subcode** do próximo 403 sem expor segredos; validar escopos da credencial de staging. Publicação real exige autorização explícita.
- [x] PRs #181/#182 integrados apenas em staging, CI [#521](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41383960919) e [#524](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41384879285) passaram, Render deploy `dep-dbk0garm8hqs738a375g` SHA `64922d82` ficou live; browser carregou a página e seletor 14:30 sem erro. Checar o novo PR de falha parcial antes de encerrar.

## Limites e decisões

- Sem migração SQL: a tabela `schedulers` é usada também por Agora e por histórico, e o Supabase é comum à produção.
- Os slots exibem **última execução conhecida daquele dia/hora**, não todos os envios históricos; eventos antigos fora dos 500 mais recentes podem aparecer como “Programado”.
- Em caso de falha de leitura do histórico da fila, a UI não deve inventar uma postagem bem-sucedida.
- A resposta 403 específica não é “corrigida” sem seu código Meta e checagem de autorização real; código novo melhora diagnóstico, classificação e sigilo.


## Complemento pós-smoke: falha 403 histórica (02/11/2026)

O primeiro deploy staging do PR #181 (`4ffc0f7`) ficou **live** e `GET /api/health/ready` retornou `{"status":"ok"}`. A tela abriu com sessão pré-existente, mas uma falha de 01/11 foi exibida como “Sem confirmação” devido à diferença entre `activities.bot_post_failure` e `publish_jobs.unknown` na versão antiga. Correção adicional proposta: somente eventos antigos com `published_parts=0`, erro HTTP 4xx **na criação do primeiro contêiner**, mesmo scheduler e término a até 5 minutos são tratados como “Erro” (evidência definitiva, sem reenviar). Falhas na etapa `threads_publish` sem prova de resultado continuam “Sem confirmação”. Em caso de envio parcial comprovado, a UI mostra “Erro parcial”, preservando o job como `unknown` e exigindo reconciliação para evitar duplicação.


### QA do formulário em staging (02/11/2026)
Abertura real do modal no Chrome de staging confirmou dois tabs (Agora/Recorrente), catálogo com radio de seleção única e troca de produto sem manter o anterior. A opção de recorrência revelou **uma regressão na expressão regular de horas**: o código renderizava barras escapadas em excesso e acusava erro mesmo para `09:00`. A correção usa classe de dígitos real `\\d` em regex JavaScript e adiciona contrato frontend em CI, além dos testes backend. Não foi criado nenhum post durante o teste.


### Investigação read-only do 403 parcial no banco (02/11/2026)
A consulta somente leitura ao Supabase compartilhado mostrou que as ocorrências de **domingo 01/11 às 15:00 e às 18:00**, no post recorrente reproduzido por Rafa, ficaram `publish_jobs.status=unknown` e registraram `activities.activity_id=2` com `stage=publish`, HTTP 403 durante `Failed to Create Media Container` e, crucialmente, `published_parts=1` (total registrado como 3 na execução). Portanto, não é correto tratar a ocorrência inteira como erro sem publicação; uma parte anterior pode estar na rede. Este é o motivo factual de a regra do PR #182 (`published_parts=0` para falha definitiva) não ter reclassificado esses horários.

Complemento corretivo em branch separada: sem alterar status de fila ou habilitar reenvio, a **apresentação** exibe `Erro parcial` por horário e `Falha parcial` na lista/detalhes, com aviso de conferência. O erro técnico fica só com ADMIN, em detalhes recolhidos por horário e no resultado da última execução; USER vê título resumido do post + horário e aviso simples. A validação exige conferir o estado externo do Threads antes de qualquer retry, com autorização do titular. Não houve SQL de escrita, migração, remoção de dados nem postagem real.


### Refinamento de organização visual do compositor (02/11/2026)
A seção **Mídia (imagem/vídeo)**, incluindo escolha de arquivos locais, avisos e carrossel, foi reposicionada integralmente para depois da opção **Usar fotos dos produtos Shopee na publicação** e antes de **Persona da IA**. Foi preservado o mesmo input nativo oculto, sem alterar validação, envio ou upload. O formulário de edição também usa a mesma ordem visual, sem duplicar o seletor. Contrato de ordem inserido nos testes de frontend.
