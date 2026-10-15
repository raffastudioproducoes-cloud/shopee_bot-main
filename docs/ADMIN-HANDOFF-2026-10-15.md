# Auto Orbital — painel ADMIN, observabilidade e globo: handoff de 15/10/2026

## Leia primeiro: estado e limites

Este documento registra implementação **local**, não uma funcionalidade publicada. O dono pediu preservar o que estava pronto e não fazer commit/push do código. O pedido posterior de atualizar o Vault autoriza documentação no repositório documental; não autoriza publicar o código do produto, mudar credenciais, aplicar migrações ou fazer deploy.

O painel pertence exclusivamente ao ADMIN. Funções comuns (produtos, listas, posts, credenciais comuns, perfis etc.) continuam na superfície comum. Há uma única navegação superior: visão geral, usuários, logs e diagnóstico. Não reintroduzir menus laterais/docks/botões repetidos.

O pedido mais recente também autorizou implementar coletores de custos, uptime, pool, consultas caras, fila detalhada e funil completo. **Esses novos coletores ainda estão pendentes**, não confundir autorização ou plano com código implementado. Moeda confirmada pelo dono: **real brasileiro (BRL)**. Provedor de cobrança não informado.

## Onde o trabalho existe

| Local | Estado verificado nesta sessão |
| --- | --- |
| `C:\Users\rafae\Documents\Projetos\_tmp\admin-refinement-local` | Cópia de trabalho atual, sem `.git`; todos os refinamentos novos estão aqui. |
| `C:\Users\rafae\Documents\Projetos\_tmp\wt-admin-panel` | Worktree-base `feat/admin-panel`, HEAD `70805cde1fe4f4f4ab9d3d1e3243d60dae13123b`; preservado e limpo. |
| `C:\Users\rafae\Documents\Projetos\ShopeeAutoVendas-local\repo` | Checkout de staging, HEAD observado `b860aff`; preservado e limpo. Revalidar HEAD antes de integrar. |
| `admin-refinement-local\refinements.patch` e `CHANGES.txt` | Delta revisável contra a base 70805cd; regenerar após alterações. Não é patch diretamente garantido contra staging/main atuais. |
| `C:\Users\rafae\Documents\Projetos\_tmp\admin-refinement-source.zip` | Archive da base 70805cd usado para gerar o delta. |
| `http://127.0.0.1:18766/admin/overview` | Prévia isolada atual; somente loopback. Não é o backend real. |
| `http://127.0.0.1:18765` | Prévia-base anterior; não confundir com a versão refinada. |

Uma IA em nuvem não terá acesso automático a esses arquivos locais. A documentação do Vault não contém o código-fonte nem o patch: para continuar a implementação é necessário acesso ao PC/cópia atual, ou entrega explícita do patch pelo dono. Não reconstruir a funcionalidade fingindo que o código já está no GitHub.

## Infra de referência, sem segredos

- Produto: `raffastudioproducoes-cloud/shopee_bot-main`; staging para testes e main para produção, conforme decisões posteriores às notas históricas de master no Vault.
- Supabase: projeto `autovendas`, referência `wcentenooirmwwlwlljp`. Não usar o projeto MiauDelier.
- Render: workspace confirmado pelo dono **Raffa Studio Produções**. Serviço correto de produção: `srv-da6vrla6iojc7380a13g`, `shopee-bot`, em https://dashboard.render.com/web/srv-da6vrla6iojc7380a13g .
- Serviço de staging `srv-daukgs17lnhs738tpl50` é outro alvo; não misturar suas métricas com produção.
- Autorização dos conectores Supabase/Render no Codex permite consultas por essas ferramentas. **Não fornece automaticamente credenciais ao backend da aplicação.** Nenhuma credencial de conector deve ser copiada, exposta ou colocada no frontend.

Os caminhos de Drive e informações de versão em notas anteriores do Vault são históricos. Estes caminhos descrevem apenas esta entrega local; este trabalho não promove uma nova versão nem substitui outras decisões de armazenamento.

## O que foi implementado

### Área administrativa e privacidade

- Rotas `/admin/overview`, `/admin/users`, `/admin/logs`, `/admin/credentials`; `beforeLoad` com guarda ADMIN e revalidação do papel pelo servidor.
- Backend registra o router administrativo em `api/main.py`; prefixo `/admin` depende de `_require_admin`. Usuário não autenticado/USER é rejeitado antes da consulta a provedores.
- A visão geral consulta `GET /admin/metrics?days=7|30|90`; no site o cliente usa `/api/admin/metrics` pelo proxy existente.
- CRUD administrativo reaproveita handlers de usuários, sem duplicar regras de negócio.
- `/admin/logs` projeta somente método, template de rota registrado, status, duração e data. Remove valores de IDs, queries, redirects, IPs, nomes e textos de erro. Usa somente rotas APIRoute registradas; caminho desconhecido recebe rótulo genérico.
- `/admin/credentials/status` retorna estados e rótulos permitidos, sem mensagens livres dos provedores ou credenciais. Cache distinto da página comum.
- Cache de métricas é preservado em falha transitória, com aviso e horário; 401/403 impede continuar exibindo cartões antigos. Ausência de dado não vira zero.

### Métricas suportadas pelo código local

- Contas atuais, cadastros de contas que ainda existem, exclusões preservadas na auditoria, planos do perfil principal e atividade autenticada nos últimos cinco minutos. Atividade recente não é presença exata.
- Volume diário e comparação com período anterior; atual inclui hoje incompleto, anterior contém dias completos. Dias/limites são controlados no servidor.
- Quantidade de requisições, erros >=400, erros 5xx, respostas 429 da aplicação, média/p95/p99 de duração. 429 da aplicação não é 429 de rede social.
- Tamanho do banco, conexões e max_connections; bloqueios, transação aberta mais antiga visível ao coletor; tamanhos de tabelas/índices de uma lista permitida. Não expõe SQL, parâmetros ou identificadores de consultas.
- Render: CPU, memória, limites e banda, com unidades e timestamps reais. Anéis calculam uso/limite somente com unidades e momentos compatíveis. CPU sem amostra fica indisponível.
- Quantidade de agendamentos cadastrados, eventos de publicação com sucesso/falha e contas existentes que publicaram no período. Agendamentos incluem recorrências; não são fila pendente. Eventos não equivalem a posts únicos.
- Retorno semanal: contas existentes com requisição autenticada bem-sucedida nos últimos sete dias, sete dias anteriores e em ambas as semanas. Não é retenção por coorte de cadastro nem duração de uso.
- Consumo por plano atual: requisições identificadas e duração acumulada, sem duplicar principal repetido. Duração inclui espera; não representa CPU, cobrança ou custo.
- Avisos de bloqueio/transação longa/429 e CPU/RAM recente alta. Sugestões de investigação, sem qualquer ação automática de escala.

### Histórico diário preparado, ainda não ativado

`database/migrations/051_admin_metrics_snapshot.sql` prepara:

- `admin_metrics_snapshot(integer)`: RPC de agregados com janela 7–90 dias, SECURITY INVOKER, search_path vazio e acesso apenas ao service_role.
- `admin_capacity_daily`: tabela agregada, RLS habilitada e acesso restrito ao service_role.
- `admin_capture_capacity()`: captura com upsert por dia de Brasília; último tamanho observado do banco e maior número de conexões observado nas capturas do dia. Retém 90 datas.

A leitura do painel não grava histórico. Nenhum job de captura foi criado, e a migração não foi aplicada no banco real. Não há previsão de esgotamento sem histórico representativo e cota real. Pico observado não equivale a pico contínuo.

### Design, globo e interações

Referências do dono: vídeo `C:\Users\rafae\Documents\snapinsta-1792036013127.mp4`; GIF `C:\Users\rafae\Downloads\download.gif`; imagens HUD UI 2020 e Seedtag Liz em Downloads. Preservar fontes/tokens atuais, grafite/ciano/índigo, tamanhos e hierarquia das referências; não copiar marca/conteúdo de terceiros.

- Gráficos com curvas suaves que preservam amostras, grades discretas, áreas transparentes, anéis de planos/capacidade e tabelas equivalentes acessíveis. Sem gráficos ou localização fictícios no modo real.
- Modal nativo com foco/Escape/restauração de foco; animações respeitam movimento reduzido.
- Globo geométrico esférico em SVG, projeção ortográfica e ocultação do hemisfério traseiro. Continentes derivados do Natural Earth 110m: 5.032 pontos em asset JSON local de cerca de 45 kB, domínio público, sem tiles/SDK externo/dependência nova.
- Arraste/toque/setas giram o globo; botões/teclas e roda do mouse controlam zoom entre 1× e 3×. Ctrl+roda mantém a ampliação do navegador.
- Rotação automática ilustrativa oeste→leste, com inclinação visual de 23,44°; não é simulação astronômica em tempo real. Ritmo lento, controle de pausa, pausa por hover/foco/zoom, documento oculto ou globo fora da tela; preferência de movimento reduzido impede auto-rotação.
- Barras de rolagem do ADMIN usam tokens do design system, inclusive documento e regiões internas. Modo de alto contraste preserva cores do sistema.
- Globo oferece seleção Mundo/Brasil e foco em RJ na demonstração. Regiões cartográficas desta versão são limitadas; códigos não mapeados precisam de cobertura separada.
- Luz ciano indica atividade recente, cinza ausência de atividade recente, vermelha exclusão histórica agregada. Cinza não comprova logout. Cada ponto é uma região, nunca uma pessoa/endereço. Cadastros atuais = atividade recente + ausência de atividade; exclusões ficam separadas.
- Demonstração é opt-in e identifica todos os números como fictícios. **Backend não publica geografia/presença atualmente**; modo real não mostra pontos. O tipo opcional `AdminMetrics.geography` prepara apenas o consumidor visual.

## Arquivos principais e responsabilidades

| Superfície | Arquivos na cópia local |
| --- | --- |
| Bootstrap/guarda/base ADMIN | `api/main.py`, `api/routers/admin.py`, `frontend/src/router.tsx`, `frontend/src/pages/AdminLayout.tsx` e guarda de autenticação existente |
| Contrato e coleta | `api/admin_metrics.py`, `frontend/src/api/adminMetrics.ts` |
| Privacidade das projeções | `api/admin_views.py`, `frontend/src/api/logs.ts`, `frontend/src/api/credentials.ts`, `frontend/src/pages/LogsPage.tsx`, `AdminCredentialsPage.tsx` |
| Banco | `database/migrations/051_admin_metrics_snapshot.sql` |
| Visão geral/escala | `frontend/src/pages/AdminOverviewPage.tsx`, `frontend/src/components/admin/ScaleMetrics.tsx` |
| Gráficos/unidades/tempo | `frontend/src/components/admin/MetricTrend.tsx`, `metricsPresentation.ts` |
| Globo | `frontend/src/components/admin/LocationGlobe.tsx`, `globeGeometry.ts`, `globeLand.json` |
| Tema e acessibilidade | `frontend/src/styles/admin.css`; `frontend/src/components/ui/Button.tsx` encaminha aria-label/aria-pressed, coberto por regressão |
| Testes | `tests/api/test_admin_area.py`, `test_admin_metrics.py`, `test_admin_privacy.py`, `test_admin_scale_metrics.py`, `tests/database/admin_metrics_sql.mjs`, `frontend/tests/admin-*.test.mjs`, `button-aria.test.mjs`, `metric-trend.test.mjs`, `metrics-presentation.test.mjs` |
| Documentação da entrega | `LOCAL-REFINEMENTS.md`, `design-qa.md`, `docs/ADMIN-METRICS.md`, `ADMIN-FUTURE-COLLECTION.md`, `ADMIN-GLOBE.md`, este handoff |

`CHANGES.txt` enumera o delta de refinamentos contra 70805cd. Bootstrap/guarda/modal e outras funções já existentes na base podem não aparecer nesse delta. Não portar apenas a lista de arquivos novos sem comparar a base.

## Prévia: não levar o servidor de demonstração para o produto

`.tmp/admin_preview.py` serve o build e endpoints fictícios locais, com seed de autenticação apenas para a demonstração. `.tmp/metrics_snapshots.json` contém agregados de consultas anteriores; `.tmp/scale-snapshots.json` contém consultas SELECT reais de 7/30/90 dias feitas em 15/10/2026, sem aplicar a função/migração. O histórico diário novo foi substituído por lista vazia nessa consulta avulsa, pois a tabela ainda não existe remotamente.

Render mantém amostras anteriores, marcadas como antigas. Usuários/atividade visual da prévia são fictícios e há rodapé identificando o cenário. Atualizar a página não consulta automaticamente Supabase/Render reais. O botão de demonstração do globo tem dados totalmente fictícios e não usa esses snapshots.

Modos do arquivo `.tmp/preview-mode.txt`: snapshot, failure, unavailable, loading e comparison (comparação sintética explicitamente identificada). Fixtures, harness, provas, servidor de prévia, build/dist e node_modules não integram o patch de produto. Nunca copiar autenticação fictícia da prévia para o site.

## Como integrar corretamente no site/backend

1. Ler este handoff, instruções atuais do repo e `docs/CODEX-NAVIGATION-GUIDE.md` se existir. Revalidar HEAD/dirty tree/CI e revisar `CHANGES.txt`/`refinements.patch`. Não descartar trabalho concorrente.
2. Usar staging/checkout isolado autorizado. A base ADMIN é 70805cd; o patch é complemento dessa base. Conferir quais mudanças da base já existem no destino e portar o conjunto necessário com revisão. Não aplicar cegamente o patch em main/staging divergente.
3. Validar autenticação real: store revalida `/api/auth/me`; servidor exige ADMIN em todos os `/admin/*`. Testar conta comum, sessão ausente, expirada e papel revogado; nenhuma deve consultar/exibir dados administrativos em cache.
4. Manter TanStack Router `/admin/*`, router FastAPI registrado e cliente HTTP apontando para `/api`. Desenvolvimento Vite proxy `/api`→FastAPI; produção usa proxy/catch-all existente em `web/routes/api_proxy.py`, `web/routes/spa.py` e bootstrap Flask/Gunicorn. Recarregar `/admin/overview`/logs/users diretamente não pode virar 404 nem cair em template legado. Build Vite e assets devem ser servidos pela topologia já suportada; não criar outro servidor só para este painel.
5. Banco: revisar migração 051, colisão de numeração e permissões da service role no ambiente alvo. Executar primeiro o teste PostgreSQL descartável. Quando a aplicação real da migração for autorizada, aplicar em ambiente de teste, confirmar RPC e validar retorno. Testar a migração completa no Supabase/PostgREST; PGlite não substitui esse smoke test.
6. Backend: credenciais existentes de Supabase são server-side. Configurar, somente quando autorizado, `RENDER_METRICS_API_KEY` e `RENDER_SERVICE_ID` com o serviço correto. Não usar prefixo VITE para segredos. Adaptador Render faz chamadas fixas de CPU/memória/limites/banda, timeout e sem redirects. Ausência de configuração/amostra permanece explícita.
7. Verificar `REQUEST_LOGGING_ENABLED`. Sem logging, atividade recente e novos indicadores dependentes de logs são indisponíveis; não ligar logging silenciosamente. Avaliar retenção/índices/custo de agregação conforme volume, sem expor logs pessoais no frontend.
8. Histórico: após autorização separada, criar um único job server-side chamando `SELECT public.admin_capture_capacity()` na frequência definida. Evitar duplicar jobs em múltiplas instâncias. Não usar heartbeat do Codex ou navegador como infraestrutura de coleta. Confirmar calendário de Brasília, idempotência, retenção e observabilidade das falhas.
9. Smoke em staging com conta ADMIN/USER, dados ausentes, falha de um provedor, timeout, 401/403, unidades/timestamps, filtros 7/30/90, comparação, gráficos/tabelas e preferências acessíveis. Validar que respostas não carregam segredos, IDs, IPs, hashes, SQL bruto ou mensagens livres.
10. Só depois de aprovação de integração/deploy: publicar backend e frontend juntos, aplicar configuração/migração autorizadas, validar serviço e disponibilidade real e observar a coleta. Esta entrega documental não executa nenhum desses passos remotos.

## Testes e evidências

- API completa: 740 testes passaram antes das últimas extensões opcionais de histórico/consumo; 20 testes focais de métricas passaram depois, incluindo supressão com logging desativado e timestamp UTC. Não afirmar que uma suíte completa posterior foi rodada sem verificar o log.
- Frontend: 59 testes passaram na etapa do globo; ajustes posteriores de rotação/roda/tema têm testes de geometria e devem ter o log final conferido em `.tmp/frontend-globe.log`.
- `npm run build` inclui TypeScript + Vite. Aviso preexistente de bundle principal >500 kB continua; não impede build, não equivale a teste de desempenho em produção.
- PostgreSQL descartável PGlite passou: migração/reaplicação, ACL/RLS, planos principais repetidos, períodos, rejeição de amostras futuras, retorno semanal positivo, captura idempotente e rollback. Sem URL/credenciais/rede de banco.
- Revisões independentes geral, Python, SQL, TS e React. Foram corrigidos custo de EXISTS correlacionado na retenção, token SVG inexistente, atributos ARIA perdidos no Button e conflito hover/foco/Ctrl+roda.
- Conferência no navegador: Brasil→RJ, zoom, teclado e arraste; celular sem overflow horizontal. Provas em `.tmp/proofs/`. Revalidar interações após alterações novas.

Comandos de referência (no diretório da cópia local, PowerShell):

```powershell
$env:SUPABASE_URL = ''
$env:SUPABASE_KEY = ''
$env:DOTENV_DISABLED = '1'
& 'C:\Users\rafae\Documents\Projetos\ShopeeAutoVendas-local\repo\.venv\Scripts\python.exe' -m pytest tests/api --confcutdir=tests/api -q
# Em frontend/:
node --test tests/*.test.mjs
npm run build
# Na raiz, runtime descartável opcional já utilizado:
npm install --prefix .tmp/db-harness --no-save --package-lock=false --ignore-scripts @electric-sql/pglite@0.5.10
node tests/database/admin_metrics_sql.mjs
```

Não rodar pytest da raiz sem isolamento: conftest legado pode inicializar banco/migrações. Não reutilizar env de produção para testes. `frontend/node_modules` nesta cópia é junction de outro checkout; não alterar dependências compartilhadas sem necessidade.

Gerar/verificar patch sem aplicá-lo:

```powershell
& 'C:\Users\rafae\Documents\Projetos\ShopeeAutoVendas-local\repo\.venv\Scripts\python.exe' .tmp/build_patch.py
git -C 'C:\Users\rafae\Documents\Projetos\_tmp\wt-admin-panel' apply --check 'C:\Users\rafae\Documents\Projetos\_tmp\admin-refinement-local\refinements.patch'
```

`--check` não aplica alterações. Não fazer git apply, cherry-pick, commit, push, merge ou deploy apenas porque há comandos neste documento.

## Próximas tarefas autorizadas, ainda NÃO concluídas

| Coletor | O que falta construir | Critério mínimo de conclusão |
| --- | --- | --- |
| Custos BRL | Fonte de fatura/uso por fornecedor, orçamento, câmbio datado quando custo vier em USD e atribuição por plano/conta ativa/publicação. Provedor de cobrança dos clientes ainda desconhecido. | Separar confirmado/estimado/indisponível; moeda/período/timestamp; sem usar plano cadastrado como pagamento nem duração HTTP como CPU. |
| Uptime | Sondas externas de liveness/readiness/latência, janela/downtime/amostragem. Endpoints health/ready existentes são insumos, não um histórico de disponibilidade. | Janela observada e lacunas explícitas; 5xx/ausência de logs não substituem uptime. |
| Pool | Descobrir métricas e privilégios do pool/Supavisor; conexões de clientes/servidor, fila/limites/saturação. | Não chamar count(pg_stat_activity) de ocupação do pool; timeout/ausência de permissão visíveis. |
| Consultas caras | Coletor agregado de pg_stat_statements/estatísticas disponíveis: frequência, tempo total/médio e contenção, sem SQL/params/IDs. | Validar reset/janela/permissões/versão e carga; não expor SQL nem executar consulta cara para medir consulta. |
| Fila detalhada | Instrumentar scheduler/adaptadores com execução idempotente: início, fim, status, tentativas, idade do pendente e 429 do provedor. | Distinguir job recorrente de tarefa pendente, evento de sucesso de post único; preservar user_id/profile_id internamente sem expor identidades no painel. |
| Funil/coortes | Eventos explícitos/idempotentes de cadastro, primeira conexão válida, primeira publicação real concluída e cobrança confirmada/cancelamento. | Coortes com denominador/período; exclusões/retries não duplicam; conexão cadastrada não prova publicação/pagamento. |
| Geografia/presença | Fonte autorizada aproximada país/UF, grupos mínimos e cobertura desconhecida; presença com expiração; logout explícito; exclusões somente agregadas com período. | Sem dados individuais/GPS/endereço/IP no painel; supressão de grupos pequenos e complementares; demonstração nunca vira dado real. |
| Ativação | Migração/configuração/jobs e integração backend real em staging. | Autorização de alterações remotas + smoke funcional, antes de produção. |

Rollback de banco somente quando autorizado e com avaliação do histórico: remover `admin_metrics_snapshot(integer)`, `admin_capture_capacity()` e `admin_capacity_daily`. Remover a tabela perde agregados; não executar silenciosamente. Frontend/backend devem voltar em conjunto a uma versão compatível. Não excluir a cópia local, patch ou provas antes da integração/revisão.
