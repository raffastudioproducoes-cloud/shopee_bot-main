# Desempenho e economia de requisições — 09/11/2026

## O que foi medido (leitura do código e do banco, sem tráfego sintético)
- A listagem de Posts fazia ~9 consultas ao banco **por post**, uma depois da outra: 90 posts por página = 800+ idas ao banco (>30 s, o limite do proxy). A conta de Rafa tem 903 posts.
- O banco é pequeno (≤1 mil linhas por tabela, exceto `request_logs` com ~29 mil): o gargalo era a **quantidade de idas e voltas**, não a varredura de tabelas. Os índices existentes já cobriam as buscas por `post_id`.
- Em produção o painel recarregava a lista de Posts inteira a cada 30 s enquanto houvesse qualquer post agendado (uma campanha de 450 posts nunca parava de consultar).
- Os arquivos do site (JS/CSS) eram revalidados a cada visita (uma requisição por arquivo).

## O que mudou (3.10.2 e 3.11.1)
| Mudança | Efeito |
|---|---|
| Listagem de Posts em lote (`IN (...)` por blocos de 15) em vez de 9 consultas por post | ~270 → ~20 consultas por página de 30; o número não cresce com o histórico de cada post |
| Resultado idêntico ao anterior (teste de equivalência com 24 posts, threads, falhas parciais, perfis/contas alheias) | sem mudança visível |
| Página buscada: 90 → 30 posts | resposta mais rápida; a tela segue em 15 por página |
| Consulta periódica de Posts: 30 s só com envio em andamento; 5 min se só há agendados; nada sem agenda | corta o "poll" permanente |
| Arquivos com hash (`/assets`): cache de 1 ano, imutável; vídeos e imagens públicas: 1 dia | menos uma requisição por arquivo a cada visita |
| Imagens de listas (produtos, catálogo) carregam sob demanda | menos dados no primeiro carregamento |
| Migração 096: índices compostos para a listagem e 8 chaves estrangeiras sem índice (alerta do Supabase) | prepara o crescimento por conta; sem mudança de dados |

## Pendências recomendadas (cada uma em PR próprio)
1. **Cache curto da autenticação** (usuário + sessão revogada + perfil): hoje cada chamada da API faz 2–3 consultas só para autenticar. Cache de ~10 s com invalidação em logout, troca de senha e exclusão de conta. Exige revisão de segurança; para vários servidores, usar Redis (a mesma chave do limite de requisições distribuído).
2. **Cache de leitura rara** em memória/Redis: limites de plano (`plan_limits`), papel do usuário, credenciais conectadas.
3. **Endpoint de resumo do painel** que devolva em uma chamada o que hoje são várias.
4. **Retenção de `request_logs`** (29 mil linhas e crescendo): arquivar/limpar por data.
5. **Revisar os 29 índices "não usados"** apontados pelo Supabase (hoje o tráfego é baixo; não remover agora).

## Preparação para escalar na horizontal (balanceador)
- Pronto: API sem estado (sessão em JWT), arquivos no Supabase Storage, listagem com número de consultas estável.
- Falta antes de 2+ instâncias: limite de requisições em Redis (já suportado por `RATELIMIT_STORAGE_URI`; produção ainda em memória), **agendador único** (hoje cada instância sobe o seu; precisa de líder/lock), cache compartilhado e pool de conexões do banco. Dependem de upgrade de plano e foram adiadas por decisão de Rafa.

## Status final (09/11/2026, staging 3.12.0)

| Item | Situação | Evidência / motivo |
|---|---|---|
| Índices de leitura de Posts e chaves estrangeiras (migration 096) | **Feito**, em produção (3.11.0) | 12 índices criados e verificados |
| Listagem de Posts em lote (consultas ≤ 4× para 60 posts), página de 30 | **Feito**, em produção | Testes de equivalência e contagem de consultas |
| Atualização automática só com envio em andamento (30 s) ou agendado (5 min) | **Feito**, em produção | `postsRefreshInterval` |
| Cache de arquivos do site (`/assets` imutável 1 ano; público 1 dia) | **Feito**, em produção | `tests/web/test_spa.py` |
| Imagens com carregamento tardio, páginas pesadas sob demanda (apresentação) | **Feito**, em produção | Chunk da apresentação lazy (~67 kB gz) |
| Retentativa da conexão HTTP/2 com o banco (causa do erro em Posts) | **Feito**, em produção | `tests/api/test_database_resilience.py` |
| Fonte hospedada no próprio site (sem pedido ao CDN bloqueado) | **Feito** (3.11.0 em produção) | `/fonts`, cache de 1 dia |
| **Cache dos limites de plano** | **Não feito, de propósito** | Um teste existente (`test_policy_changes_and_downgrade_are_not_cached`) fixa a regra de que mudança de limite e downgrade valem na hora. O ganho era de 1 consulta por chamada; não compensa quebrar a regra |
| **Cache do login (usuário/sessão)** | **Não feito, de propósito** | Cada requisição confere usuário, sessão revogada e versão da senha. Um cache, mesmo curto, deixaria logout, troca de senha e conta apagada valendo por alguns segundos, e com várias instâncias a invalidação precisaria de Redis. Revisão de segurança antes |
| **Dashboard** | **Já é 1 endpoint** (`/dashboard/stats`: 4 contagens + 2 recentes) | Mantido sequencial: o paralelismo foi o que amplificou a falha da conexão em Posts. Reavaliar com o upgrade de plano |
| **Retenção de `request_logs`** (~29 mil linhas) | **Decisão de Rafa pendente** | A política de privacidade descreve os logs como "append-only"; apagar linhas antigas muda esse texto legal. Proposta: reter 90 dias e atualizar a política junto |
| **Índices sem uso** (35 no total) | **Revisado: manter** | Todos têm 8–16 kB (≈ 0,5 MB no total) e a maioria cobre chave estrangeira (protege exclusões em cascata). Apagar não rende nada e pode piorar `DELETE` de conta |
| **Várias instâncias com balanceador** (trava do agendador, Redis) | **Adiado** até o upgrade de plano | O limitador já usa Redis/Valkey (S-04); falta eleger um único agendador e validar o despachante central |
| **Teste de carga (k6)** | **Adiado** com o upgrade | Medir o limite real exige o plano pago; o gratuito dorme |

### Medições disponíveis
- Primeira chamada de Posts após o deploy da staging: 5,2 s para 30 posts (instância acordando e abrindo conexão nova). Depois disso, `GET /posts?limit=30` responde 200 em tempo normal nos logs. Não foi feita medição comparativa em outras páginas.
