> **08/11/2026 — ESTADO CANÔNICO: AUTO ORBITAL 3.6.2 EM PRODUÇÃO.** Rafa homologou a correção do HTTP 502/cronômetro em staging e autorizou PATCH e main. PR #368/CI #1172 SUCCESS → staging `13d74a0f`, Render `dep-dbofjam8bjmc73b6gkrg` LIVE; PR #369/CI #1174 + gate SemVer #12 SUCCESS → main `bf558c644d6f42b28baccf766eff0825e17a1d17`, Render produção `dep-dbofl50ae00c739m8bq0` LIVE. Health/readiness/login 200 e HTML público 3.6.2, sem novo request 5xx observado; `SIGTERM` do worker antigo esperado. `VERSION=3.6.2`, staging/main com arquivos idênticos; sem migração, cron, gateway ou postagem real. QA autenticada pelo agente em produção não feita. [Release e limites](RELEASE-3.6.2-20261108.md). Notas anteriores sobre 3.6.1 vigente/staging-only são históricas.

> **08/11/2026 — ACEITE DO REQUISITO DE UPLOAD NA STAGING:** Rafa relatou testes aprovados para timeout corrigido/cronômetro de mídia e autorizou release PATCH 3.6.2. Implementação já testada na staging; a verificação de produção ainda depende do gate CI/SemVer, merge e Render. [Release](RELEASE-3.6.2-20261108.md).

> **08/11/2026 — REQUISITO CORRETIVO EM STAGING (PATCH candidata 3.6.2):** eliminar 502 prematuro do proxy ao esperar processamento MP4 em Produtos, preservando sanitização. No painel com sombra/skeleton/círculo, exibir tempo decorrido após transferência e notificações de processamento (0/15/30/60/120 s), sucesso ou falha persistente e botão de conferir galeria sem reenvio. Erro de timeout como 504 explicativo. [Aceite e limites](UPLOAD-502-TEMPO-PROCESSAMENTO-20261108.md). Sem mudança na versão oficial 3.6.1 ou em produção.

> **08/11/2026 — EVIDÊNCIA NOVA:** PR app #366/CI #1168 **SUCCESS** → staging `33d73d97572ce0ee736d535f1cbfe35a11bb3314`, Render `dep-dboep9qvcj2c739apqug` **LIVE**, health/readiness/login HTTP 200. Testes locais 1.308 API, 34 web, 33 frontend correlatos, 5 SemVer e build PASS. **Ainda falta QA autenticada de Rafa; sem merge main nem bump de VERSION=3.6.1.** [Critérios e limites](UPLOAD-502-TEMPO-PROCESSAMENTO-20261108.md).

> **08/11/2026 — ACEITE DA PATCH 3.6.1 EM PRODUÇÃO:** Rafa confirmou MP4 aceito na staging e download da imagem Shopee funcionando, aprovou versão e promoção; CI/SemVer e deploy produção tiveram sucesso. MP4 original sanitizado com FFmpeg e guarda estrita; UX sombreada/skeleton/anel percentual real, processamento separado e prévias com loading/fallback. Testes automatizados 1.308 API e 99 frontend; API/UI produção saudáveis; falhas de rede reais sob carga não homologadas. [Release](RELEASE-3.6.1-20261108.md).

> **08/11/2026 — REQUISITO EM STAGING (PATCH candidata 3.6.1):** vídeos MP4 legítimos exportados com metadados `uuid` devem ser aceitos quando passarem pelo processamento seguro (nunca armazenar bytes originais opacos). Na edição do Produto, mostrar sombra na área de mídia, skeleton de pré-visualização e anel com porcentagem **real** de envio; após 100% mostrar processamento separado até resposta da API. Suportar celular, múltiplos arquivos e acessibilidade. Sem ampliar cota, formato, Storage, redes ou publicar automaticamente. [Contrato e casos de aceite](UPLOAD-MP4-PROGRESSO-20261108.md).

> **08/11/2026 — ENTREGA DO PRODUTO 3.6.0 EM PRODUÇÃO:** download autenticado da foto Shopee no catálogo; descrição personalizada persistente de Produtos é o padrão para novos posts imediatos/recorrentes e campanhas. Criar Post e cada item da Campanha podem substituir texto com edição/IA apenas na instância local, preservando o catálogo; restauração manual disponível em campanhas. PR #357 mergeada à `main` `699e81bd`, Render produção `dep-dbod0q7b9u1s73dhci7g` LIVE, health/readiness OK, CI e SemVer verdes. QA autenticada e integrações reais seguem sem comprovação; mídias adicionais da galeria não migram automaticamente. [Contrato](PRODUTOS-DESCRICOES-CAMPANHAS-20261108.md) · [Release](RELEASE-3.6.0-20261108.md).

> **04/11/2026 — CONTRATO ATUAL DA DASHBOARD E RETENÇÃO (release 3.2.0 em regularização):** a dashboard é uma visão **da conta**, agregando todos os perfis, inclusive dados históricos de perfis arquivados; no Free há só o perfil principal, Pro até 3, Premium até 5 e ADMIN sem teto comercial. Exclusão de perfil secundário deve arquivar a identidade e preservar histórico concluído/conciliável, enquanto filas não despachadas podem ser canceladas. Exclusão integral de conta inclui banco, Storage e Auth, somente por fluxo seguro solicitado. Banco único compartilhado, migrações 080–086; flags destrutivas OFF até homologação. Abaixo permanecem decisões históricas de planejamento.

> **Decisão de produto de 03/11/2026 (planejada, não entregue):** downgrade e cancelamento da renovação não reduzem acesso até acabar o período pago; upgrade após confirmação e ativação, com possível espera de algumas horas. Avisos imediatos e sete dias antes da renovação; e-mails de conta/segurança separados de marketing opt-in. Direito de arrependimento/reembolso é fluxo distinto. Fonte: [política F4 §12](PLANOS-F4-POLITICAS-E-FASES-20261103.md#12-transições-de-assinatura-e-comunicação--decisão-corrigida-de-rafa-03112026). Sem checkout/cobrança implementados.

> **Decisão confirmada F4B2 em 03/11/2026:** perfil principal obrigatório. Free = 1 perfil total (nenhum adicional); Pro = 3 totais (1+2); Premium = **5 totais** (1+4); ADMIN sem limite comercial. Compartilhados na conta: produtos, Shopee, IA/Gemini. **Isolados por perfil: listas (Rafa confirmou manter), social OAuth, posts criados/agendados/publicados/recorrentes, histórico, campanhas e mídias.** Aplicação gradual no staging: RPC de perfil respeita limites e trigger legado segura `main` em três perfis até release próprio. Ver [contrato F4](PLANOS-F4-POLITICAS-E-FASES-20261103.md). Status não equivale a DB aprovado/deploy concluído.

> **Decisão de produto 03/11/2026 — planos:** Free/Pro/Premium, regras comerciais e exceção ADMIN no [contrato F4](PLANOS-F4-POLITICAS-E-FASES-20261103.md). As seções históricas abaixo não prevalecem sobre a nova decisão. Não divulgar recursos Premium de teto ainda indefinido como “ilimitados”.

> **02/11/2026 — Correção de isolamento entre os schedulers de staging e main (implantação em etapas):** o mesmo Supabase permanece, mas agendas novas terão `schedulers.environment` conforme o branch Render; jobs anteriores ficam na produção. APScheduler passa a usar `apscheduler_jobs` em main e `apscheduler_jobs_staging` em staging; recuperação/claims da fila verificam o ambiente e dono. Ativação de staging só depois de a main receber estes filtros. Detalhes, verificação e rollout em [SCHEDULER-ENVIRONMENTS-20261102.md](SCHEDULER-ENVIRONMENTS-20261102.md). Nenhuma publicação externa é validada por CI.

> **02/11/2026 — Correção dos posts em desenvolvimento (staging, ainda não publicada):** seleção de um produto, retirada de agendamento avulso, seletor desktop em 24h, histórico do estado de cada ocorrência, última postagem confirmada e erro simplificado para usuário. Supabase compartilhado impede apagar esquema/legado; erro HTTP 403 do Threads precisa de código Meta e autorização antes de declarar publicação funcionando. Detalhes e QA: [POSTS-AJUSTES-RECORRENCIA-20261102.md](POSTS-AJUSTES-RECORRENCIA-20261102.md). **Não alterar main/produção.**

> **Escopo real de 31/10/2026:** o Guia Mestre distingue o que está implementado, condicional, planejado ou indisponível (ex.: X/Kwai/Shopee Vídeo). Não tratar esta fotografia histórica como prova de publicação externa. **Primeira leitura obrigatória:** [AGENTS.md](../AGENTS.md) e [docs/GUIA-MESTRE-IA.md](GUIA-MESTRE-IA.md).

# PRD — Shopee Auto Vendas

> **07/11/2026 — decisão comercial Shopee para próxima versão (somente staging):** o cliente não fornece mais App ID/Secret Shopee para garimpo, apenas ID de afiliado por conta. A chave da plataforma serve ao catálogo e fica com ADMIN; links do cliente são construídos via `an_redir` com o ID específico. Comissões continuam condicionadas à Shopee, sem prometer elegibilidade ou atribuição sem QA. Migração 090 e detalhes em [contrato Shopee](SHOPEE-API-GLOBAL-ID-AFILIADO-20261107.md). Trechos abaixo que exigem credencial manual Shopee por usuário são históricos da 3.4.0.

> **07/11/2026 — IA DA PLATAFORMA (produção LIVE 3.4.0):** clientes não cadastram chave de IA. A plataforma fornece o serviço e só ADMIN gerencia provedor/modelo/chave/teste em `/admin/credentials`; o card saiu de `/credentials` para todos. Migração 089 aplicada com segredo ADMIN cifrado e isolamento staging/produção. PR de promoção #314 passou CI #1049 e SemVer #4, main `4ca125f`, Render produção `dep-dbndgcnb9u1s73cip6mg` LIVE, health/ready OK. Ver [contrato](IA-PLATAFORMA-ADMIN-20261107.md). Trechos anteriores sobre chave por usuário são históricos da 3.3.0; QA autenticado ainda não comprovado.

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
padrão são as credenciais da Shopee; a IA é fornecida pela plataforma. Kwai não possui
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
| Copywriter IA | Geração de texto de post por persona com credencial central da plataforma (Gemini/OpenAI/Anthropic, `apis/llm.py`) | `api/routers/platform_ai.py` |
| Credenciais | Shopee manual por usuário, redes sociais por OAuth; IA somente em `/admin/credentials` para gestão pelo ADMIN, nunca reexibe segredo | `api/routers/credentials.py`, `api/routers/platform_ai.py` |
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
- Produtos salvos e credencial Shopee pertencem à conta e são reutilizados pelos perfis.
- A chave de IA pertence à plataforma e é compartilhada entre contas, isolada por ambiente.
- Cada perfil preserva suas proprias redes conectadas, listas, posts, midias, agendamentos,
  resultados, notificacoes e preferencias de publicacao.
- Usuario comum conecta redes por OAuth; nao recebe formulario de token manual, portal de
  desenvolvedor, log tecnico nem mensagem que revele uma area administrativa.
- ADMIN usa a mesma experiencia comum e, apos autorizacao confirmada pelo servidor, recebe
  modulos adicionais para contas, logs e homologacao manual de redes.

## 6. Critérios de sucesso

- Usuário conecta uma rede social clicando em "Conectar" e sem colar segredo nenhum
  (exceto Shopee; a chave de IA é administrada somente pela plataforma).
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
> **07/11/2026 — CADASTRO / CONTRATAÇÃO FUTURA (layout revisado):** nome completo, CPF, e-mail e senha obrigatórios no cadastro por e-mail; Google dispensa senha local. Celular obrigatório antes de compra de plano, demais dados pessoais opcionais **editáveis dentro do card do perfil principal** em `/profiles` (não em formulário externo à lista). Cards secundários mostram somente imagem e nome. Identidade de pagamento será **da conta, não de perfil social**. Contratação/renovação ainda não estão implementadas; CPF criptografado, readiness calculado em API; e-mail autenticador só altera por fluxo verificado, ainda não disponível. [Contrato](CADASTRO-IDENTIDADE-PLANOS-20261107.md).

> **07/11/2026 — PERFIS SEM DADOS PESSOAIS DUPLICADOS:** perfis secundários identificados apenas por nome e foto (foto opcional). Criação/edição do perfil não solicita contatos/endereço; estes ficam no formulário editável do titular dentro do card principal da conta. Cota de perfis não exibe tag de plano; botão de upgrade somente quando aplicável. Ativação e gerenciamento continuam operacionais.
