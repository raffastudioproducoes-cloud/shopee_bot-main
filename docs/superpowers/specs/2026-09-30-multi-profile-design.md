# Design — Sistema de Múltiplos Perfis + Fluxo Git Flow com Staging

> Origem: pedido direto de Rafa, 2026-09-30, detalhado por spec próprio + esclarecimentos
> em conversa. Este documento é a autoridade vinculante para o plano de implementação que
> virá depois (`superpowers:writing-plans`). Nenhum código deve ser escrito antes deste
> documento ser aprovado por Rafa.

## 1. Contexto e motivação

Hoje o Shopee Auto Vendas é **1 conta = 1 usuário = 1 "loja"**: toda credencial (Shopee,
redes sociais), todo produto, toda lista e todo post pertence diretamente a um `user_id`.
Rafa quer permitir que uma única conta (login) gerencie **até 3 lojas/perfis** separados,
com isolamento total de dados entre eles — inspirado no benchmarking do projeto irmão
MiauDelier Manager (item 10.9 do backlog, `docs/TASK.md`), mas com limite de 3 em vez de 10.

Junto disso, o fluxo de desenvolvimento do projeto muda de "push direto em `master`" (prática
histórica documentada em `docs/RULES.md` item 1) para um modelo Git Flow com staging,
dado o risco de uma migração de schema tão ampla afetar o único usuário real em produção
(`rafastudio`).

## 2. Modelo de dados

### 2.1 Tabela nova: `profiles`

```sql
create table public.profiles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  kind text not null check (kind in ('principal', 'secundario')),
  plan_tier text not null default 'free' check (plan_tier in ('free', 'plus', 'premium')),
  nome text not null,
  email text not null,
  telefone text,
  endereco text,
  avatar_url text,
  created_at timestamp not null default now(),
  updated_at timestamp not null default now()
);
create index idx_profiles_user_id on public.profiles (user_id);
alter table public.profiles enable row level security;
create policy "block_all_api" on public.profiles for all using (false) with check (false);
```

- No máximo 1 `kind='principal'` e no máximo 2 `kind='secundario'` por `user_id` — validado
  na aplicação (não em constraint de banco, para manter a mesma abordagem simples já usada
  no resto do projeto).
- `plan_tier` é só um rótulo hoje — **não há sistema de cobrança/plano pago implementado
  neste projeto**. Todo perfil nasce `free`. A tag Free/Plus/Premium aparece na UI mas não
  há lógica de enforcement (ex: não há bloqueio de feature por plano). Isso é uma decisão
  explícita de escopo (YAGNI): construir billing real não foi pedido.

### 2.2 Migração aditiva do dado existente (RULES.md item 8: nunca destrutivo)

Migração cria a tabela `profiles` e, na mesma migração (ou num script de dados executado
uma vez), gera automaticamente 1 linha `kind='principal'` para **cada usuário já existente**
(hoje só `rafastudio`), copiando `username` como `nome` inicial e um `email` placeholder se
o usuário não tiver um campo de e-mail hoje (confirmar: `users` tem coluna `email`? Se não
tiver, `profiles.email` nasce vazio/null e o usuário edita depois — não travar a migração por
isso).

### 2.3 `profile_id` nas tabelas existentes

Todas as tabelas hoje filtradas por `user_id` (identidade de LOGIN) passam a também ter
`profile_id` (identidade de LOJA): `products`, `product_lists`, `posts`, `medias`,
`shopee_credentials`, `threads_credentials`, `x_credentials`, `facebook_credentials`,
`instagram_credentials`, `tiktok_credentials`, `kwai_credentials`, `credential_checks`,
`activities`, `schedulers`, `audit_events`, `request_logs`.

- `profile_id uuid references profiles(id) on delete cascade` (nullable na migração inicial,
  depois de popular via o perfil principal de cada `user_id`, pode virar `not null` numa
  migração seguinte — duas etapas, mesmo padrão de "aditivo, nunca quebra conta existente").
- Toda query do backend que hoje filtra só por `user_id` passa a filtrar por
  (`user_id`, `profile_id`) — `profile_id` vem do "perfil ativo" da sessão (ver 2.4).
- **Exceção Shopee**: `shopee_credentials` **não** tem `unique constraint` na API Key —
  a mesma chave pode estar salva em mais de um perfil (pedido explícito de Rafa). Sem
  auto-preenchimento entre perfis: o usuário cola a chave de novo manualmente em cada
  perfil novo, mesmo que seja a mesma.

> **Nota (2026-10-05) — divergências entre este spec e a implementação** (verificadas em
> `database/migrations/036`, `038`, `039` e `api/routers/profiles.py`; o texto acima fica como
> registro do que foi aprovado):
>
> - **FK com `ON DELETE SET NULL`, não `ON DELETE CASCADE`.** Em todas as tabelas com
>   `profile_id` (036 e 038) a FK usa `on delete set null`. Motivo, registrado no cabeçalho das
>   migrações: excluir um perfil não deve apagar dado de negócio (produtos, posts, credenciais,
>   atividades etc.) — a linha continua existindo, só perde a ligação com o perfil.
>   (A FK `profiles.user_id -> users` segue `on delete cascade`, como na seção 2.1.)
> - **Exceção Shopee implementada pela 039.** A migração `039` removeu o UNIQUE de
>   `shopee_credentials.app_id` (`shopee_credentials_app_id_key`), permitindo a mesma API Key em
>   mais de um perfil. Também trocou o UNIQUE `(user_id, network)` de `credential_checks` por um
>   índice único `(user_id, profile_id, network)`.
> - **Nome do claim: `profile_id`, não `active_profile_id`** (seção 2.4 abaixo). O JWT carrega
>   `profile_id`, e `GET /auth/me` devolve o `profile_id` ativo para o frontend.
> - **Limite de 3 perfis também no banco**: a migração `037` adiciona trigger
>   `trg_enforce_profile_limit` (advisory lock + recontagem) além da checagem em `POST /profiles`.

### 2.4 Perfil ativo na sessão

O JWT (cookie httpOnly já existente) ganha um claim `active_profile_id`. Trocar de perfil
(`POST /profiles/{id}/activate` ou similar) reemite o cookie com o novo claim, sem exigir
novo login. Todo endpoint que hoje lê só `user_id` do token passa a também ler
`active_profile_id` e filtrar por ele.

## 3. Papéis: admin vs. usuário comum (reaproveita padrão já existente)

O projeto já tem esse padrão implementado em `CredentialsPage.tsx`/`api/routers/credentials.py`
(sessão de 2026-09-29, commit `4320519`): usuário comum só vê status + conectar/desconectar
OAuth; admin vê campos manuais de colar API/token/ID, botão "Testar conexão", e pode criar
outros usuários de login. **Perfis reaproveita exatamente esse padrão de visibilidade por
tag de acesso** (`users.access`), não inventa um novo.

### 3.1 O slot de menu "Usuários" vira "Perfis"

- Renomeado no menu lateral e na rota (decidir: manter `/users` internamente e só trocar o
  label, ou renomear rota para `/profiles` — recomendo renomear a rota também, por clareza,
  com redirect de `/users` para compatibilidade).
- **Admin**: vê os cards de Perfis (própria conta) **e** mantém acesso à função de gerenciar
  contas de login de outros usuários da plataforma (a função atual de `UsersPage.tsx`) —
  dentro da mesma página, como uma seção/aba extra visível só para admin, não um menu
  separado novo.
- **Usuário comum**: vê só os cards dos próprios Perfis (principal + secundários), sem
  nenhuma opção de criar conta de login nova (mantém a restrição atual).

### 3.2 Design dos cards de Perfil

- Formato quadrado com bordas arredondadas (reusa token de radius existente, ex: `--r-lg`),
  imagem do usuário (avatar) ocupando o card, informações abaixo (nome, e-mail).
- Duas etiquetas coloridas pequenas, nessa ordem: (1) plano — `Free`/`Plus`/`Premium`;
  (2) tipo — `Principal`/`Secundário` (nomenclatura final: manter esses dois termos em
  português, já usados por Rafa na conversa — evita ambiguidade com "Primary/Secondary" em
  inglês misturado no meio da UI).
- Reusa o componente de tag/badge já existente no projeto se houver um (`StatusBadge` — ver
  `frontend/src/components/ui/`), com cores via tokens existentes, nunca hex novo.

## 4. Novas rotas de frontend

- **`/profiles`** (era `/users`): grid de cards conforme seção 3.2. Ações: trocar perfil
  ativo, editar perfil, criar novo perfil (respeita limite de 3, botão desabilitado com
  tooltip quando no limite). Upload de avatar (ver seção 5).
- **`/settings`**: página nova, configurações da conta matriz (não por perfil — é por
  login). Módulo de segurança: trocar senha, exigindo a senha atual (mesmo padrão já
  usado no reset de senha de `auth.py` e na autoexclusão de conta, `pwd_context.verify()`
  antes de aplicar).

## 5. Avatar — Supabase Storage

- Novo bucket no Supabase Storage (ex: `avatars`), público para leitura (URLs de avatar
  precisam carregar no `<img>` sem autenticação complexa) mas só gravável via service_role
  (backend faz o upload, nunca o cliente direto).
- Upload via device: usuário seleciona arquivo no navegador → `POST /profiles/{id}/avatar`
  (multipart) → backend valida tipo/tamanho (reusar `fleep` já usado em `posts.py` para
  magic-byte, mesmo padrão) → sobe pro bucket → salva a URL pública em `profiles.avatar_url`.
- Extração via OAuth (Google/Apple) no login: **não aplicável hoje** — o login deste
  projeto é usuário/senha próprio (bcrypt), não há OAuth de login social implementado.
  Este sub-item do pedido original fica fora de escopo nesta rodada (documentar como
  "não aplicável à arquitetura de auth atual", não como pendência).

## 6. Fluxo Git Flow + Staging + SemVer

### 6.1 Branches e ambientes

- `main` (renomear de `master`, ou manter `master` como nome e só aplicar a regra — decidir
  com Rafa: GitHub usa `main` por padrão em repos novos, mas este repo já se chama `master`
  historicamente; renomear branch é uma operação de baixo risco mas visível — **perguntar
  antes de renomear**, já que muda a branch padrão que todo clone/CI referencia).
- `staging`: branch + ambiente próprio.
  - Infra: **novo Web Service no Render, plano free**, apontando pra branch `staging`
    (deploy automático nela, igual ao `cd.yml` atual mas outro `serviceId`).
  - Banco: mesmo projeto Supabase (`autovendas`) usando uma **branch de banco do Supabase**
    (feature de branching do Supabase, disponível no free tier com limitações) — evita o
    custo de um segundo projeto Supabase, mas isola o schema de teste do de produção.
    Se o branching de banco do Supabase free tier não cobrir o caso de uso na prática,
    fallback é um schema Postgres separado dentro do mesmo projeto (`staging.*` em vez de
    `public.*`) — decisão tomada durante a implementação, não trava o design.
- Branches de feature: `feature/multi-profile`, etc. — nunca commitada direto em `main` nem
  `staging` sem merge.

### 6.2 Proteção de branch

`main`: exige PR, bloqueia force-push, bloqueia commit direto (inclusive do próprio Rafa).
`staging`: mais permissiva (permite merge direto de `feature/*` sem PR formal, já que é
ambiente de teste) — decisão pragmática para não burocratizar demais um projeto solo.

### 6.3 Versionamento semântico

- Arquivo `VERSION` ou `package.json`/`api/__init__.py` (decidir durante implementação)
  guarda `vX.Y.Z`.
- Versão só sobe no merge pra `main` (nunca em commits de branch de feature/staging).
- Patch: merge de correção de bug. Minor: merge de feature nova sem quebra. Major: mudança
  arquitetural (ex: este próprio multi-perfil, se for considerado "major" — a decidir: dado
  que é aditivo e não quebra conta existente, pode ser tratado como Minor; Major fica
  reservado pra mudança que quebra compatibilidade de verdade).

## 7. Fora de escopo nesta rodada (YAGNI, documentado explicitamente)

- Billing/cobrança real por trás das tags Free/Plus/Premium.
- Login social via OAuth (Google/Apple) — logo, extração de avatar via provedor OAuth.
- CODEOWNERS, assinatura GPG de commit, OIDC para nuvem — não se aplicam a projeto solo sem
  deploy via IAM de nuvem (ver decisão já registrada na sessão sobre boas práticas GitHub).

## 8. Decisões finais (aprovado por Rafa, 2026-09-30)

1. **Renomear `master` → `main`.** Segue a prática padrão de devs. A renomeação de branch
   no GitHub redireciona automaticamente clones/PRs antigos; `cd.yml`/`ci.yml` e qualquer
   referência a `master` no repo precisam ser atualizados para `main` no mesmo commit.
2. **`/profiles` substitui `/users`.** Sem coexistência, sem redirect permanente — a rota
   antiga deixa de existir.
3. **Este multi-perfil é versão MAJOR** (`v1.x.x` → `v2.0.0`), não Minor. Justificativa do
   Rafa: agrega uma função "grande" — muda o modelo de dados de toda a aplicação (1 conta
   = 1 loja → 1 conta = até 3 lojas), mesmo sendo uma migração aditiva que não quebra a
   conta existente do ponto de vista de dados.

Spec aprovado. Próximo passo: `superpowers:writing-plans` para o plano de implementação.
