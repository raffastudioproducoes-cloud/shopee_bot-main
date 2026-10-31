> **Escopo real de 31/10/2026:** o Guia Mestre distingue o que está implementado, condicional, planejado ou indisponível (ex.: X/Kwai/Shopee Vídeo). Não tratar esta fotografia histórica como prova de publicação externa. **Primeira leitura obrigatória:** [AGENTS.md](../AGENTS.md) e [docs/GUIA-MESTRE-IA.md](GUIA-MESTRE-IA.md).

# PRD — Shopee Auto Vendas

> Documento canônico vivo. Cenário A (projeto existente) — todo o conteúdo abaixo vem do
> código, do histórico git ou dos documentos já existentes neste repositório e no vault
> Obsidian (`Projetos/ShopeeAutoVendas/` em `C:\Users\rafae\Documents\Obsidian`). Itens sem
> evidência estão marcados **[A CONFIRMAR COM O USUÁRIO]**. Última verificação: 2026-09-29.

## 1. O quê

**Shopee Auto Vendas** é um SaaS que automatiza a divulgação de links de afiliado da Shopee
em redes sociais. Um único painel cobre: garimpar/cadastrar produto, gerar texto de post com
IA, agendar ou publicar na hora, e acompanhar tudo por histórico de atividades.

Para o usuário leigo, conectar uma rede social é um clique em "Conectar [rede]" — ele nunca
vê nem cola Client ID/Secret de app nenhum (modelo de **app único**: o dono do SaaS registra
um único app por rede social, o usuário final apenas autoriza via OAuth). Antes do redirecionamento,
o produto explica quais dados e permissões serão solicitados. As exceções manuais do cliente
padrão são a credencial da Shopee e a chave de IA do provedor escolhido. Kwai não possui
postagem automática enquanto não houver API pública adequada.

ADMIN também usa o mesmo OAuth por perfil, mas pode usar overrides manuais de diagnóstico
para Threads, X, Facebook, Instagram, TikTok e Kwai. Essa possibilidade é protegida no backend;
esconder o formulário no frontend não é considerado controle de acesso.

## 2. Por quê (problema)

Quem divulga produto de afiliado hoje faz manualmente: procurar produto elegível, escrever
texto de venda, postar em cada rede social na hora certa, sem histórico de erro nem
retentativa. Fonte: `README.md` (seção Objetivo) e `docs/ROADMAP_MIGRACAO.md`.

O objetivo do produto é tirar esse trabalho manual:
- garimpar produto elegível (comissão, vendas, categoria) sem sair do painel;
- gerar copy com IA (Gemini) por persona, sem escrever do zero toda vez;
- agendar ou publicar na hora, com retry e log de falha — sem post perdido silenciosamente;
- organizar produtos em listas reaproveitáveis entre posts;
- conectar credenciais de cada rede social de forma cifrada, nunca expostas de volta na tela;
- acompanhar o que foi feito por atividade, com histórico auditável.

## 3. Usuários-alvo

Dois níveis de acesso (`api/routers/auth.py:246`, `api/routers/users.py`):

| Papel | O que vê/faz |
| --- | --- |
| **ADMIN** | Tudo: cria/edita usuários, vê diagnóstico cru de conexão, usa OAuth por perfil e pode inserir override técnico manual quando necessário para teste |
| **USER** | Status da própria conexão + "Conectar/Desconectar" OAuth por rede. Nunca vê nem envia token social, e nunca vê o texto de erro cru (`check_message: null` pra não-admin) |

Cadastro público (`POST /auth/register` em `api/routers/auth.py`) **sempre** cria com
`access="USER"` — o cliente nunca consegue se auto-promover a ADMIN pelo formulário.

Hoje em produção existe **1 usuário real** (`rafastudio`, ADMIN) — confirmado via consulta
SQL read-only ao Supabase, registrada no vault (`00-INDICE-Estado-Atual.md`, 2026-09-28).
Multi-tenant com múltiplos usuários pagantes é visão pós-MVP, não implementada
**[A CONFIRMAR COM O USUÁRIO — se já existe intenção de abrir para usuários externos]**.

## 4. Funcionalidades principais (MVP)

| Módulo | Recursos | Fonte |
| --- | --- | --- |
| Garimpo/Produtos | Cadastro/edição de produto Shopee (URL colada, valida contra a API deles) | `README.md`, `database/products.py` |
| Listas de produtos | Agrupamento reaproveitável entre posts | `database/product_lists*.py` |
| Posts | Criação, thread multi-parte, composição por rede de texto/mídia, agendamento (cron/data) ou publicação imediata, retry e log de falha. Rede incompatível não bloqueia as demais: recebe texto válido com aviso quando a API suporta publicação sem mídia, ou fica fora com motivo claro | `api/routers/posts.py`, `scheduler/`, `docs/superpowers/specs/2026-10-11-composicao-midia-por-rede-design.md` |
| Copywriter IA | Geração de texto de post por persona com a chave de IA do próprio usuário (Gemini/OpenAI/Anthropic, `apis/llm.py`) | `README.md` |
| Credenciais | Shopee e IA por valor manual do próprio usuário; redes sociais por OAuth do app único. Overrides sociais/Kwai são ADMIN-only e nunca reexibem segredo | `api/routers/credentials.py` |
| Atividades | Histórico auditável de ações do usuário | `database/activities.py` |
| Usuários | Administração de acesso ADMIN/USER | `api/routers/users.py` |
| Perfis | Até 3 perfis (lojas) por conta, com avatar. Atualização 2026-10-05 (branch `chore/phase-12-integration`): o isolamento por perfil cobre também posts, mídias, credenciais das redes, dashboard, notificações, logs e backup/restore; a versão anterior desta linha dizia só produtos e listas | `api/routers/profiles.py`, `database/migrations/038`, frontend `ProfilesPage` |
| Configurações | Troca de senha da conta | `api/routers/settings.py`, frontend `SettingsPage` |
| Scheduler | Jobs agendados in-process (APScheduler, jobstore em Postgres) | `scheduler/`, ADR `19-ADR-Scheduler-In-Process.md` (vault) |

### Redes sociais — estado real por rede (evidência: código + consulta SQL ao Supabase em
2026-09-28, documentada em `vault/00-INDICE-Estado-Atual.md` do Obsidian)

| Rede | OAuth implementado | Usuário real conectado (token salvo) | Publicação testada com sucesso |
| --- | --- | --- | --- |
| **Threads** | Sim, app único | **Sim** — único caso confirmado | Não confirmada nesta verificação |
| **X (Twitter)** | Sim, app único (migrado de per-user) | Não — `user_access_token` nulo | Não |
| **Instagram** | Sim, app único (Facebook Login for Business) | Não — `user_access_token` nulo | Não |
| **Facebook** | Sim, app único (reaproveita app do Instagram, migrado depois do token de Página manual) | Não confirmado — credencial existe mas nunca validada | Não |
| **TikTok** | Sim, app único; domínio/prefixo e redirect staging validados | Sim no staging — Rafa confirmou conexão/autorização em 2026-10-09 | Não |
| **Kwai** | Não — sem API pública de postagem confirmada (só API de anunciantes/ads) | N/A | N/A |

> **Nota de precisão**: um contexto de sessão anterior, fornecido junto com esta tarefa,
> afirmava que "Threads, X, Facebook, Instagram" estavam "funcionando end-to-end, testado e
> confirmado". Essa afirmação **não é sustentada pela evidência real** (código +
> consulta SQL). Desde 2026-10-09, TikTok também tem conexão/autorização confirmada no
> staging por teste do Rafa. X/Instagram ainda têm o app único implementado e a UI de
> "Conectar" pronta, mas dependem de alguém concluir o fluxo OAuth — isso é uma ação pendente
> de Rafa/usuário em produção, não um gap de código. Ver `docs/MEMORY.md` para o detalhe
> completo.

TikTok está disponível por OAuth para usuário comum. Kwai permanece fora da publicação automática
por não haver API pública apropriada. X, Facebook e Instagram também usam cards completos de
conexão OAuth; a autorização e o token resultante pertencem exclusivamente ao usuário e perfil
que iniciaram o fluxo.

> **Atualização 2026-10-05**: a seção 4 acima descreve 2026-09-29. Desde então, nesta branch
> (ainda não mergeada em `main`), o multi-perfil passou a isolar quase todos os dados por
> `profile_id` (migrações 037-042) e a UI de perfis ganhou editar/excluir/ativar sem reload. O
> estado das redes sociais não mudou. Pendências manuais de Rafa: ver `docs/TASK.md` item 10.13.

## 5. Fora do escopo do MVP

- Kwai com postagem automática (sem API pública confirmada).
- Multi-tenant com planos pagos, cobrança — visão registrada em
  `17-Visao-Expandida-Shopee-IA.md` (vault), não aprovada como sprint.
- Garimpo automático por filtro (comissão/vendas/categoria) e dashboard de ROI real
  (clique/comissão) — mesma visão pós-MVP, não implementados no código atual.
- Mobile app.

## 5.1 Conta, perfis e papeis

- Uma conta pode manter o perfil principal e mais dois perfis.
- Produtos salvos, credencial Shopee e configuracao/chave de IA pertencem a conta e sao
  reutilizados pelos tres perfis.
- Cada perfil preserva suas proprias redes conectadas, listas, posts, midias, agendamentos,
  resultados, notificacoes e preferencias de publicacao.
- Usuario comum conecta redes por OAuth; nao recebe formulario de token manual, portal de
  desenvolvedor, log tecnico nem mensagem que revele uma area administrativa.
- ADMIN usa a mesma experiencia comum e, apos autorizacao confirmada pelo servidor, recebe
  modulos adicionais para contas, logs e homologacao manual de redes.

## 6. Critérios de sucesso

- Usuário conecta uma rede social clicando em "Conectar" e sem colar segredo nenhum
  (exceto Shopee e a chave de IA escolhida pelo próprio usuário).
- Post agendado é publicado no horário certo pelo scheduler, com log de falha visível.
- Credencial de rede social nunca é reexibida em nenhuma resposta da API.
- Cadastro público nunca cria usuário ADMIN.
- A troca de perfil nao permite ler, publicar ou testar uma conexao social de outro perfil.
- Uma pessoa comum nao recebe bundle administrativo; acesso direto a rota administrativa retorna
  para a area comum e o backend continua recusando a operacao protegida.

## 7. Riscos e dependências

- Dependência de disponibilidade e política das APIs externas (Shopee, Threads, X,
  Meta/Facebook/Instagram, TikTok) — fora do controle do time.
- TikTok "Direct Post" público exige aprovação de parceiro da TikTok for Developers
  (`requirements.txt`/`.env-example` — comentário em `apis/tiktok.py`) — bloqueio externo.
- TikTok Login Kit também exige que o `redirect_uri` cadastrado no painel bata exatamente com
  `TIKTOK_CALLBACK_URL`; em 2026-10-09 o provedor estava rejeitando a conexão por
  `redirect_uri` antes de devolver o callback. A causa operacional confirmada no staging foi
  que o app Live do TikTok tinha só a URL de produção cadastrada; staging precisa estar
  cadastrado como Redirect URI adicional no Login Kit. Resolvido no staging em 2026-10-09:
  Rafa confirmou autorização concluída e conta conectada.
- Threads pode bloquear contas que não aceitaram convite de tester/role enquanto o app Meta
  não estiver público/aprovado; erro observado em usuário comum:
  `The user has not accepted the invite to test the app` (`error_code=1349245`).
- Coexistência Flask (legado, produção) + FastAPI (nova API) no mesmo container é uma
  topologia ainda não validada 100% em produção no Render (ver `docs/MEMORY.md`).

## Referências

- `README.md` (raiz do repo)
- `docs/ROADMAP_MIGRACAO.md`, `docs/CHECKLIST_MIGRACAO.md`
- Vault Obsidian: `00-INDICE-Estado-Atual.md`, `00-Resumo-e-PRD.md`, `17-Visao-Expandida-Shopee-IA.md`

## Atualização 2026-10-13 - decisão de marca futura

Decisão aprovada em 2026-10-13: a marca futura do produto será **Auto Orbital**. Implementação ainda pendente; o produto, runtime, frontend, infra e documentação viva ainda não foram convertidos. Ver `docs/rebranding/34-Rebranding-Auto-Orbital-Plano-Mestre.md`.
