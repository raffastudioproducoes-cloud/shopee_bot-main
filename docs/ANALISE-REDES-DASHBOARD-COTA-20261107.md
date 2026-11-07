# Análises — dashboard e cota diária de atualização manual (07/11/2026)

Estado: implementação candidata publicada em staging (PRs #337 e #338; migração 092 aplicada e RLS verificada). Ajuste de interface em andamento: retirada das duas tabelas redundantes. **Não promover a main sem aprovação expressa de Rafa**. Versão atual `3.4.0`; evolução MINOR na candidata `3.5.0`.

## Layout e indicadores
- Seis indicadores distintos: total de envios; taxa de confirmação; quantidade de redes com atividade; visualizações oficiais de posts; interações mensuradas (curtidas/comentários/reposts/cliques); posts com insights oficiais e IDs rastreáveis.
- Seis painéis de gráficos/estado: série temporal por dia; comparação horizontal por rede de concluídos/falhas/sem confirmação; composição das interações; distribuição de envios por dia da semana UTC; ranking dos cinco posts com mais visualizações oficiais; estado das nove redes do catálogo.
- Catálogo visual: Facebook, Instagram, Kwai, Shopee Vídeo, Telegram, Threads, TikTok, WhatsApp, X. Redes futuras ou sem coletor homologado exibem indisponibilidade; métrica ausente = **—**, jamais 0 presumido. O filtro Rede inclui as nove opções, com aviso de indisponibilidade quando a API não suporta consulta.
- Fontes: `GET /analytics/summary`, `GET /analytics/timeline`, `GET /analytics/posts` autenticados; apenas posts realmente publicados pelo Auto Orbital, por conta e perfil, inclusive histórico de perfis arquivados em Todos. Nunca somar métricas globais de conta ou Página ou duplicar IDs externos. A coleta oficial por post permanece limitada às APIs homologadas, não se criam números fictícios.

## Interface compacta — PATCH subsequente

- Remover exclusivamente as tabelas duplicadas `Detalhamento por rede` e `Desempenho por publicação`, no desktop e no mobile; preservar **todos** os seis KPIs e seis painéis de visualização, bem como filtros e botões.
- `Situação das nove redes`: exibir, em cada card de rede com métricas oficiais, visualizações, curtidas, comentários, reposts e cliques, mantendo estado da integração, distinção entre zero e indisponibilidade e cobertura das nove redes.
- `Publicações em destaque`: ranquear até cinco posts do escopo selecionado por visualizações oficiais; incluir data de publicação (horário de Brasília), status da coleta, visualizações e quatro tipos de interação; posts confirmados sem visualizações oficiais aparecem depois e com `—`. Os registros continuam intactos no servidor.
- Sem endpoint, migration, cron, `pg_net`, fila ou alteração de dados. Os cards são apenas novas apresentações dos mesmos dados; métricas agregadas oficiais continuam restritas aos posts da plataforma.

## Limite de atualização manual — servidor
- `GET /analytics/refresh/quota`: objeto `{unlimited, used, remaining, limit, reset_at}`, escopo do usuário autenticado, sem permitir escolher usuário.
- `POST /analytics/refresh?profile_id=<UUID|all>`: autoriza somente perfis pertencentes à própria conta; `all` permite atualizar até 12 perfis com paralelismo 3; uma única atualização válida consome **um** uso da cota da conta, independente de número de perfis e plano.
- Contas USER: 10 ações manuais válidas por dia civil em `America/Sao_Paulo`; contador persistente no Supabase e incrementado atomicamente. Reset à meia-noite de Brasília. Ao alcançar o limite, HTTP 429 e botão desabilitado. Sem permissão de contornar cota trocando de perfil, plano, browser ou instância Render.
- ADMIN: ilimitado, sem cooldown de cinco minutos, mantendo lock contra duas coletas simultâneas. Usuários comuns: lock/cooldown de 300s existente na coleta; solicitação indisponível por cooldown **não** consome cota. Atualização automática a cada 24 horas é independente e não consome cota. Falhas de banco/controle bloqueiam ação manual com HTTP 503, sem publicar ou enviar conteúdo.
- `database/migrations/092_analytics_manual_refresh_quota.sql`: tabela com FK de usuário, RLS habilitado e grants só service_role; RPCs `analytics_manual_refresh_status` e `claim_analytics_manual_refresh` SECURITY INVOKER com `search_path=''`, ownership check e uso atômico. Somente aplicação aditiva no Supabase compartilhado; **não** toca nos dois `pg_cron`, `pg_net` ou Vault.
- Resposta do POST não contém tokens/segredos dos claims. O cliente invalida cache da cota, do resumo, da série e dos posts após a solicitação. Clientes anteriores que consultam apenas analytics sem refresh continuam compatíveis.

## Gate de homologação
1. Compilação `tsc && vite build`, testes frontend e Python/CI.
2. PR para `staging`, CI SUCCESS; confirmar migração aditiva e grants, sem retirar acesso preexistente da main.
3. Aplicar migração 092 no projeto Supabase **autovendas**; verificar tabela, funções, RLS, grants e cron jobs ativos sem mutação.
4. Merge somente em `staging`; Render LIVE, health/readiness e verificação visual autenticada. Registrar PR/SHA/deploy e pendências no `docs/TASK.md`/Vault.
5. `main` somente após aprovação posterior de Rafa.
