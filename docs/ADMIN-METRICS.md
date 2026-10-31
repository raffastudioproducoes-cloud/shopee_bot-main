# Métricas administrativas

`/admin/overview` e `GET /admin/metrics?days=30` exigem ADMIN. A resposta contém somente agregados e não contém senhas, hashes, IPs, identificadores de conta, serviço ou instância.

## Ativação após revisão

1. Revisar e aplicar `docs/migrations-pendentes/051_admin_metrics_snapshot.sql` (fora de database/migrations/ de propósito, para não ser aplicada no boot; só mover após autorização, pelo processo de migrações do projeto). A função é invoker, com execução restrita a `service_role`. A instalação, reaplicação e remoção foram testadas apenas em PostgreSQL descartável local; não houve DDL ou alteração de dados no banco real.
2. Usar as variáveis de conexão Supabase já existentes no backend. Não enviar chaves ao frontend.
3. Configurar as variáveis Render abaixo somente no servidor (nunca no frontend). Não usar credenciais dos plugins no aplicativo.

   | Variável | Onde | Descrição |
   |---|---|---|
   | `RENDER_METRICS_API_KEY` (ou `RENDER_API_KEY`) | Render de produção **e** de staging | Chave da API do Render com acesso de leitura às métricas. Sem ela, `render.status` = `not_configured` (sem zeros falsos). |
   | `RENDER_ADMIN_SERVICE_ID` | opcional | Default `srv-da6vrla6iojc7380a13g` (`shopee-bot` produção). O id do staging (`srv-daukgs17lnhs738tpl50`) é ignorado e substituído pelo de produção. `RENDER_SERVICE_ID` legado não é mais lido. |

   O painel de staging lê o mesmo Supabase (RPC `admin_metrics_snapshot` via `service_role` já configurado no backend) e as métricas Render de **produção**. Se a migração 051 não estiver aplicada ou a RPC falhar, `supabase.status` = `unavailable` e `counts` = `null`, nunca zeros.
4. Validar com uma conta ADMIN e uma USER: a segunda deve receber 403 antes de consultar qualquer provedor.

O endpoint coleta CPU, memória, limites de CPU/memória e tráfego do Render em 24 horas, resolução de uma hora. Mostra o horário de cada amostra; métricas ausentes ficam indisponíveis. O painel consulta a cada minuto. A conexão autorizada dos plugins do Codex serve para inspeção e não configura automaticamente as credenciais do backend.

## Dados e limites

- Contas atuais e planos do perfil principal. Planos não comprovam pagamento.
- Cadastros de contas ainda existentes no período; não reconstitui contas excluídas.
- Exclusões preservadas na auditoria. Autoexclusões antigas podem estar ausentes por uma FK corrigida neste branch; nenhum histórico foi reconstruído.
- Ativos: requisições autenticadas com resposta menor que 400 nos últimos cinco minutos. Não é presença exata. Sem registro de requisições, fica indisponível.
- Requisições, erros e latência média/p95 são do histórico disponível no aplicativo.
- Supabase: tamanho do banco, conexões e limite; não equivale a consumo total de disco, storage ou faturamento. Latência da RPC é medida separadamente.
- Origem, tempo de sessão, localização e pagamento confirmado não são coletados atualmente.

Amostras ausentes não viram zero. As curvas unem observações, preservam os valores medidos e usam a posição temporal das amostras Render. Tabelas expansíveis oferecem os valores exatos.

O painel preserva a coleta anterior se uma atualização falhar. Mostra a idade dos dados (coleta com mais de5min e amostra Render com mais de2h), diferencia cobertura parcial de indisponibilidade e oferece nova tentativa. Todos os horários de amostras são exibidos em Brasília.

`previous_period` compara cadastros sobreviventes, exclusões auditadas, requisições e erros com o período anterior de igual número de dias. O atual inclui hoje incompleto; o anterior contém dias completos, com aviso explícito. Uma base anterior zero não produz percentual infinito. Não há comparação histórica de planos/contas ativas porque esses snapshots antigos não existem.

A projeção `/admin/logs` envia apenas método, template de rota registrado, status, duração e horário UTC. Não envia IDs, IPs, nomes, queries, redirects ou diagnósticos. `/admin/credentials/status` fornece estados com rótulos padronizados, sem mensagens livres dos provedores; usa cache separado da página comum de credenciais. Os contratos legados continuam separados.

## Repetir a validação descartável

Sem instalar dependência no produto: `npm install --prefix .tmp/db-harness --no-save --package-lock=false --ignore-scripts @electric-sql/pglite@0.5.10`, depois `node tests/database/admin_metrics_sql.mjs`.

O teste usa PostgreSQL em memória sem URL de conexão, cria somente dados fictícios e verifica migração/reaplicação, serviço com RLS, rejeição anon/authenticated, planos duplicados, limites7/30/90, amostras futuras, comparação e rollback. O banco é fechado ao terminar. Runtime: [PGlite oficial](https://pglite.dev/docs/).

Plano sem coleta ativada: [ADMIN-FUTURE-COLLECTION.md](ADMIN-FUTURE-COLLECTION.md).

## Verificação real em 15/10/2026

Consultas somente leitura confirmaram as colunas e executaram o SELECT de agregação nos períodos 7/30/90 dias. No serviço Render de produção havia memória, limites e tráfego; uso de CPU e HTTP vieram sem amostras na janela consultada. A prévia local usa capturas desses agregados, identificadas como snapshot, sem atualizar os provedores automaticamente. Os cards de gestão e a atividade da prévia continuam fictícios.

Referências: [Render Metrics](https://render.com/docs/service-metrics), [OpenAPI Render](https://api-docs.render.com/openapi/render-public-api-1.json), [Supabase observabilidade](https://supabase.com/docs/guides/observability/metrics), [tamanho do banco](https://supabase.com/docs/guides/platform/database-size).
# Ampliação local de capacidade e clientes

O contrato `scale` acrescenta p99, contagens 5xx e 429 da aplicação, conexões bloqueadas e duração da transação aberta mais antiga visível, além do tamanho das tabelas permitidas e seus índices. Não retorna consultas SQL, parâmetros, usuários, IPs ou identificadores.

Publicações são eventos `activities` de sucesso/falha no período; não são posts únicos. Agendamentos são registros cadastrados, inclusive recorrentes, e não representam fila pendente. Contas que publicaram contam usuários existentes com evento de sucesso. Retorno semanal compara contas existentes com requisições autenticadas bem-sucedidas nas duas janelas adjacentes de sete dias; não é retenção por coorte nem tempo de uso.

Consumo por plano usa o perfil principal atual, sem duplicar contas com perfis principais repetidos. Requisições sem conta existente não integram essa tabela. Duração acumulada inclui espera, não mede CPU ou faturamento. Registro de requisições desativado torna esses indicadores indisponíveis.

## Histórico opcional preparado, sem ativação

A migração local 051 prepara `admin_capacity_daily` e a função `admin_capture_capacity()`, acessíveis somente ao `service_role`. A captura faz upsert por dia de Brasília, retém 90 datas e preserva o maior número de conexões **observado nas capturas**, nunca um pico contínuo. Tamanho do banco é a última captura do dia. A leitura do painel não grava histórico. Não foi aplicada em Supabase e nenhum job foi criado; ativação e agendamento remoto continuam pendentes.

Depois de revisão e implantação autorizadas, um job de backend pode chamar `SELECT public.admin_capture_capacity()` diariamente, sem credenciais no navegador. A interface mostra somente dias realmente capturados. Sem cota real e histórico representativo, não calcula previsão de esgotamento. Rollback completo: remover as duas funções e a tabela de histórico; a remoção da tabela perde apenas esses agregados e exige decisão explícita.

## Fontes ainda necessárias

- Ocupação de pool e consultas mais caras: coletor de estatísticas do Postgres, com privilégios verificados e sem SQL bruto no payload.
- Duração, idade da fila, retries e 429 do provedor: eventos de execução instrumentados no scheduler/adaptadores; 429 da aplicação não é usado como substituto.
- Disponibilidade e saturação sustentada: sondas e séries de amostras independentes; ausência de logs não prova uptime.
- Funil completo de conexão/primeira publicação e coortes: eventos explícitos e idempotentes; a contagem de contas publicadoras atual não substitui o funil.
- Custos por conta/publicação, receita, pagantes e cancelamentos: faturamento confirmado e atribuição de consumo; plano cadastrado não confirma pagamento.

Avisos locais usam apenas bloqueios/transações/429 e amostras recentes compatíveis de CPU/RAM. Nenhuma ação automática de escala foi implementada. Sem sinais disponíveis, a interface não declara a operação saudável.


## Storage global Free e egress (31/10/2026)

O mesmo ADMIN, em **Capacidade e crescimento**, mostra agora bytes ocupados e
reservados, numero de objetos por bucket, referencia da cota do plano Free
(1 GiB), percentual e horarios da amostra. Dados vem de
`admin_storage_snapshot()` (migração 058), atraves da credencial server-side
`service_role`; não retorna chaves de objetos nem IDs de usuarios. Sao
incluidos os buckets `post-media`, `avatars` e quaisquer outros do mesmo
projeto. A amostra é pontual: não corresponde a GB-hora faturado no mês.

Alertas informativos em 75% e critico em 85%; **bloqueio global
preventivo em 90%** da referencia de 1 GiB. Os tres caminhos de upload
(`/posts/media-drafts`, `/posts/product-image-drafts/{product_id}`,
`/posts/{post_id}/media` e `/profiles/{profile_id}/avatar`)
passam pela mesma reserva backend. O importador Shopee usa o mesmo pipeline
de rascunhos, portanto não cria uma rota desprotegida. A reserva transacional
conta uploads em voo entre instancias de staging e main. Uma requisicao que
excederia o limite recebe HTTP 507 antes do envio; se a medicao falhar,
HTTP 503 sem gravar arquivo novo. Reservas nao liberadas por falha do processo
expiram em 30 minutos. Cota individual por usuario/perfil **nao implementada**
por decisao do produto.

**Egress:** o consumo faturável é agregado de banco, Storage, autenticação
e demais servicos; não é a largura de banda do Render. A credencial
`service_role` do app nao fornece o total de billing da organizacao.
Por isso o painel oferece acesso direto ao **Supabase Usage** como fonte
oficial, sem exibir numero aproximado ou falsamente atualizado.
A consulta oficial do mês deve ser acompanhada pelo administrador;
não há coleta automatica de egress no backend. **Nao adicionar uma chave de
gestão do Supabase sem uma decisao posterior**, nem contratar serviços.

Para aplicar o controle: execute
`database/migrations/058_admin_storage_capacity.sql` **uma vez** no projeto
Supabase compartilhado, com privilégios de administrador, e valide suas
permissoes (apenas `service_role`). Depois implante staging, confira
`GET /admin/metrics` com ADMIN e os testes automatizados, e promova para
main. O SQL e aditivo, nao cria policies em `storage.objects` e nao inclui
migracao destructiva. A tabela `storage_upload_reservations` não armazena
identidades, objetos nem credenciais, apenas bytes, UUID e expiracao.
Em caso de falha do RPC, investigar antes de ativar uploads: a aplicacao
falha fechada propositalmente.

Referencias: [Supabase tamanho de Storage](https://supabase.com/docs/guides/platform/manage-your-usage/storage-size),
[Supabase egress](https://supabase.com/docs/guides/storage/serving/bandwidth).

A migração corretiva `059_revoke_storage_reservation_direct_grants.sql`
revoga também os privilégios diretos concedidos automaticamente pelo
Supabase a `service_role` na tabela de reservas. O backend permanece com
acesso por RPC `SECURITY DEFINER` apenas, sem consultas diretas.
