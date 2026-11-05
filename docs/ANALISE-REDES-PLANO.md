# Analise de redes: contrato e fases

## Seletor de perfil para análises (staging LIVE, 05/11/2026)

A página `/analytics` passa a oferecer **Perfil** acima de Período e Rede, com **Todos os perfis** como visão inicial e opções individuais dos perfis da conta. O seletor é apenas de leitura: não ativa nem altera o perfil operacional. Os filtros de período/rede, cartões, gráficos, tabela e a identidade visual permanecem como estavam.

- A seleção é enviada como `profile_id=all` ou UUID aos endpoints `GET /analytics/summary` e `GET /analytics/timeline`. Sem o parâmetro, clientes anteriores continuam usando o perfil ativo.
- O backend valida a propriedade do UUID (`profiles.user_id`) e aplica `publish_jobs.user_id` a todas as contagens. A visão geral inclui perfis arquivados e registros legados sem `profile_id`; a série usa o RPC existente por perfil e soma somente os registros legados de perfil nulo, sem contar duas vezes.
- Na visão geral, as métricas oficiais das plataformas não são somadas sem deduplicação de fonte. Atualização manual e testes de insights ficam disponíveis apenas para um perfil específico. Não há migrations, alterações de cron ou de serviços de agendamento.
- Os filtros e caches de consulta diferenciam usuário, perfil, período e rede, evitando exibir dados de uma seleção anterior.

**Estado:** PR #298 mesclada em `staging` (SHA `d588eb1cf77335ed9a8f8d0ac91c5b7f9c528d98`), deploy Render `dep-dbm27ne8bjmc739fcfag` confirmado `live` em 05/11/2026; registro integrado ao Vault. Não homologada funcionalmente: pytest/tsc pendentes e CI #41981263248 falhou antes dos steps (duas tentativas).

## Painéis de visualização (31/10/2026)

O frontend React apresenta a **mesma tabela detalhada de redes** após quatro cartões de KPI e quatro painéis no design system Auto Orbital (paleta Graphite / cyan / orbit blue / índigo / violeta, superfícies `Panel`), também responsivos:

1. **KPI:** envios concluídos, falhas, sem confirmação e taxa confirmada. Taxa = `succeeded / (succeeded + failed + unknown)`; exibe **—** sem envios e não presume êxito dos inconclusivos.
2. **Evolução diária:** linha de concluídos, falhas e sem confirmação; consulta `GET /api/analytics/timeline?days=7|30|90&network=...`. Cada ponto representa quantidade real de registros terminais em `publish_jobs` por data UTC, restrita à janela móvel selecionada. A janela de N×24 horas pode alcançar N+1 datas UTC.
3. **Envios por rede:** anel calculado apenas com `succeeded` por rede filtrada. Se não houver envios, anel neutro e zero, nunca amostras de demonstração.
4. **Situação dos envios:** anel com os três estados reais e legenda numérica. `unknown` significa sem confirmação, não falha ou êxito.
5. **Insights oficiais:** estados da última coleta e, quando validado, `page_media_view` da **Página do Facebook** (não do post). Dados não oferecidos pelas APIs são indisponíveis, não zero.

**Caminho e segurança:** `AnalyticsPage.tsx` consome `/analytics/summary` para KPI/anéis/tabela e `/analytics/timeline` para evolução. `social_analytics.py` autentica o usuário e o perfil ativo; a RPC `analytics_daily_job_counts` (`database/migrations/065_analytics_daily_job_counts.sql`) faz agrupamento no PostgreSQL com filtro explícito `user_id` + `profile_id` e verificação de titularidade do perfil, `SECURITY INVOKER`, `EXECUTE` exclusivo de `service_role`. Não retorna tokens, conteúdo de posts, IDs externos ou dados de outros perfis. Sem tabela de métricas extra ou dependência paga.

**Atualização:** a consulta temporal participa da invalidação acionada por **Atualizar informações**, mantém o fluxo de 24h/ao voltar à aba, e o estado de erro do gráfico não oculta a tabela principal. Estados vazios são explicativos, sem números fictícios. As sondas técnicas seguem somente para `ADMIN`.

**Testes:** `tests/api/test_social_analytics.py` valida login obrigatório, filtros rejeitados, escopo enviado à RPC, retorno vazio sem perfil e erros de banco sem vazamento de detalhes. TypeScript/Vite do frontend no CI; inspeção responsiva e comportamental deve ser feita após deploy de staging antes da promoção para `main`.


**Permissão das sondas manuais (31/10/2026):** `GET /api/analytics/summary` continua disponível ao usuário autenticado para os seus próprios dados. `POST /api/analytics/probe/{network}` (Threads/Facebook/Instagram) é ferramenta de diagnóstico **exclusiva ADMIN**, protegida por papel no FastAPI; os botões correspondentes em Análises só aparecem para `ADMIN`. Isso não amplia as permissões de insights dos provedores e não muda a tabela de resultados para usuários comuns.

Estado em 2026-10-21. As APIs abaixo oferecem conjuntos diferentes de dados; "indisponivel" nao significa zero. Nunca somar alcance unico de redes distintas como pessoas unicas globais. Cada coleta pertence a `user_id` + `profile_id` e usa somente o token desse perfil.

## Auditoria dos portais em 2026-10-21

- **Meta:** Auto Orbital permanece em modo de desenvolvimento/nao publicado. O painel de verificacao mostra a empresa Raffa Studio Producoes **em analise**; verificacao de acesso fica bloqueada ate a conclusao. Em Teste, Paginas consta concluido, Threads e Instagram constam em andamento. A tela de envio para analise desabilita o botao de envio. O conector de revisao retornou estados contraditorios (`UNSUBMITTED` com `is_approved=true`, mas `can_submit=false` por envio anterior em analise e privilegios listados como rejeitados); nao interpretar isso como aprovacao. Validar no portal antes de qualquer nova submissao.
- **Permissoes de insights Meta:** em 2026-10-21, o usuario adicionou `threads_manage_insights`, `instagram_manage_insights` e `read_insights` ao rascunho. As tres aparecem como "Pronto para teste" no portal, com zero chamadas contabilizadas. Isso nao concede escopo aos tokens existentes nem acesso avancado a usuarios comuns; o conector de revisao ainda aponta etapas de caso de uso, gravacao, precheck de API e checagem de dados pendentes. Ver [relatorio de testes reais](ANALISE-REDES-TESTES-2026-10-21.md).
- **Shopee Afiliados:** o portal `affiliate.shopee.com.br/open_api` mostra a API do afiliado atual como **Valido** (segredo nao registrado aqui). Isso nao comprova permissao operacional de cada consulta: o guia documenta erro `10035` quando o afiliado ainda nao tem acesso a Open API. A biblioteca oficial lista `conversionReport` e `validatedReport`, alem de ofertas e links curtos. Testar uma chamada autenticada com a credencial ja cadastrada, sem expor seu valor, antes de implementar ingestao.
- **Shopee conversoes:** `conversionReport` documenta `purchaseTime`, `clickTime`, identificadores de pedido/conversao/produto, status, valor e comissao, canal e tipo de atribuicao. A paginacao usa `scrollId` de uso unico/30 segundos e permite ate 500 registros por pagina; implementar coleta incremental/idempotente e retencao limitada. Nao confundir relatorio de conversoes com prova de qual post social causou a compra: isso requer identificador de link/campanha e comprovacao de atribuicao da Shopee.

Fontes oficiais desta auditoria: [Meta - app Auto Orbital](https://developers.facebook.com/apps/1804230767234146/dashboard/), [Meta - verificacao](https://developers.facebook.com/apps/1804230767234146/verification/), [Meta - testes](https://developers.facebook.com/apps/1804230767234146/test/), [Shopee Afiliados - biblioteca de API](https://affiliate.shopee.com.br/open_api/home), [Shopee Afiliados - conversionReport](https://affiliate.shopee.com.br/open_api/list?type=conversion_report). As telas Shopee exigem login do titular.

## Matriz verificada

| Rede | Dados documentados | Acesso atual do app | Proximo gate |
| --- | --- | --- | --- |
| Threads | Insights por post: views, likes, replies, reposts, quotes e shares | Novo OAuth pede `threads_manage_insights`; token anterior nao foi comprovado com esse escopo | Reconectar perfil de teste e executar sonda de leitura; depois testar `/{post_id}/insights` |
| TikTok | Display API: view_count, like_count, comment_count e share_count de videos publicos do proprio usuario | OAuth padrao pede `user.info.basic,video.publish,video.upload`, sem `video.list` | Aprovar `video.list`, reconectar e consultar `/v2/video/query/` com IDs confirmados |
| X | Lookup de post com `public_metrics` (reposts, respostas, likes, quotes) | OAuth pede `tweet.read`; conta de teste sem credito/acesso operacional | Revalidar plano, credito, ID externo e disponibilidade dos campos antes da coleta |
| Instagram | Insights por conta/midia variam por tipo e versao da Graph API | OAuth via Meta Business Login; permissao efetivamente aprovada e token precisam ser verificados | Inventariar permissoes e campos atuais no app, testar insights de midia do proprio perfil |
| Facebook | Insights de pagina/post variam por tipo e versao da Graph API | OAuth via Meta Business Login; acesso a Insights nao foi comprovado | Verificar `read_insights` e `pages_read_engagement`, token de pagina e metricas validas na versao usada |

Fontes primarias: [Threads Insights (Meta)](https://www.postman.com/meta/threads/request/ndeeu6p/get-post-insights), [TikTok Display API](https://developers.tiktok.com/docs/en/display-api-overview), [TikTok Query Videos](https://developers.tiktok.com/docs/en/tiktok-api-v2-video-query), [TikTok Scopes](https://developers.tiktok.com/docs/en/tiktok-api-scopes), [X Post Lookup](https://github.com/xdevplatform/docs/blob/main/x-api/posts/lookup/quickstart.mdx), [Instagram API (Meta)](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api).

Cliques em links de afiliado, visitas a Shopee e compras **nao** decorrem dos contadores sociais acima. A Shopee agora documenta um relatorio de conversoes, mas seu acesso efetivo e vinculo com posts ainda precisam ser testados; nao inferir conversao de views. Demografia por post nao deve ser prometida sem campo e permissao oficiais especificos. Nao usar Research API do TikTok: e destinada a pesquisadores aprovados, nao a analitica comercial deste app.

## Entrega em fases

1. **Base operacional (em staging):** pagina `/analytics`, filtro de 7/30/90 dias e rede, contagens de execucoes finalizadas da fila (`publish_jobs.finished_at`) com estados distintos. Sonda read-only para Threads, Instagram e Facebook usando credencial do perfil. Sem valores sociais simulados; API autenticada e escopada por perfil. Sem nova migracao. Deploy e bloqueio sem sessao validados; consulta autenticada e isolamento real ainda pendentes.
2. **Threads:** obter permissao de insights, mudar aviso OAuth, reconectar voluntariamente, coletar por `external_id` confirmado, tratar 403/limites/metricas ausentes, snapshots com origem e horario, testes de isolamento.
3. **Meta:** verificar permissao aprovada no app e token efetivo; implementar Facebook/Instagram com metricas especificas ao tipo de midia, sem campos depreciados e sem somar denominadores diferentes.
4. **TikTok e X:** adicionar `video.list` ao TikTok somente apos aprovacao e consentimento; X apos liberacao de acesso. Coletar IDs confirmados, observar cotas, erros e expiracao.
5. **Consolidacao:** tabela por post, tendencias e comparacao apenas de metricas semanticamente compativeis; cache por perfil, atualizacao controlada, exportacao, retencao e exclusao. Cliques/conversoes em projeto separado de atribuicao com consentimento e fonte verificavel.
6. **Shopee afiliados:** apos confirmar acesso real a `conversionReport`/`validatedReport`, mapear somente conversoes da conta titular aos links rastreaveis criados por ela; nao misturar dados compartilhados de Shopee entre perfis sem uma regra explicita de atribuicao. Testar paginacao, idempotencia, cancelamentos/validacao de comissao e privacidade antes de exibir resultados.

Gate para marcar uma rede como funcional: permissao aprovada, token do proprio usuario contendo o escopo, resposta real da API para um post proprio, ID externo persistido, teste entre duas contas/perfis e ausencia de vazamento de token em logs. Build e mocks nao substituem esse gate.


## Atualização manual e diária — implementação de 31/10/2026 (PR #140)

- Em **Análises**, USER e ADMIN possuem **Atualizar informações**. O botão envia `POST /api/analytics/refresh` com cookie autenticado, usuário e perfil ativo do próprio servidor; nunca recebe ID de outra conta via corpo.
- `GET /api/analytics/summary` mantém os contadores `publish_jobs` **em tempo real** para 7, 30 e 90 dias. Retorna também `last_attempt_at`, `last_completed_at`, `provider_states`, `auto_refresh_hours=24` e o cache validado. A leitura agenda em background o cadastro/retomada da coleta do perfil, sem bloquear o carregamento da página.
- `api/analytics_refresh.py` lê apenas credenciais da conta **e** perfil via `scope_owner`, decifra tokens exclusivamente no backend e consulta em HTTPS, em paralelo, no máximo três APIs já integradas: Threads `views`, Facebook Page `page_media_view` e Instagram `reach`. Usa timeout 15 s por chamada; não loga token, IDs externos ou resposta bruta da plataforma. TikTok/X não possuem leitor de analytics confiável habilitado e não recebem chamada fingida.
- No Facebook, períodos diários explicitamente retornados pela Meta são validados e persistidos em `facebook_daily_values`; o resumo soma **somente períodos retornados** dentro da seleção. Threads permite conferir total explícito de views, mas a tela **não** atribui ao período selecionado sem confirmação de escopo temporal. Instagram `reach` não é `views` e não preenche coluna de visualizações. Curtidas, comentários, reposts e cliques permanecem `null` até uma fonte oficial por post ser validada. Resultado API recusado/sem autorização/sem dados → estado legível, **nunca** valor inventado.
- Migration **064** cria `analytics_daily_refreshes`, chave única `(user_id, profile_id)`, RLS ativo, Data API negada a `anon/authenticated` e RPC `claim_analytics_refresh` `SECURITY INVOKER`, com `EXECUTE` só `service_role`. Claim atômico, lease de 60 s e intervalo de 24h para coleta automática impedem duplicação entre staging/main. O botão usa janela mínima de 5 minutos para proteger quotas das redes. UPDATE de resultado confere o token de claim para impedir escrita de worker obsoleto.
- `scheduler/__init__.py` verifica pendências a cada hora em um job local (`on_demand`), com lote limitado. Após cold start/suspensão Render Free, roda na **próxima hora ativa** e o acesso à página também dispara a retomada; não há promessa de execução em minuto exato enquanto o serviço estiver dormindo. A atualização de query no browser ocorre a cada 24h se a aba permanecer aberta, e ao voltar o foco. A automática se aplica aos perfis que já visitaram a página de Análises, pois são cadastrados na primeira leitura; não adiciona serviço pago ou background worker dedicado.
- Cache, timestamps e estados são por usuário/perfil e não contêm tokens, identificadores de mídia ou texto de posts. Nada é publicado nas redes por esta tarefa. Erro de conexão/API não apaga as contagens reais da fila. Cada provedor pode exigir OAuth e permissão extra antes de entregar insights.
- Verificação exigida: testes de parsing e ausência, autorização, propriedade/escopo, proteção contra claim repetido, React/TS, RLS e migração em staging, Render live e PR em main. Esta seção registra o contrato de implementação; a evidência de deploy deve ser acrescentada após a conclusão do CI.
