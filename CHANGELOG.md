# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento [SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

## [3.6.1] - 2026-11-08

### Fixed / Changed — MP4 válido e progresso real de mídia (PATCH 3.6.0 → 3.6.1; homologada por Rafa)

- Corrige rejeição de MP4 H.264/AAC com caixa estrutural `uuid` de topo limitada no preflight; vídeos são obrigatoriamente reconstruídos via FFmpeg e sanitizados novamente com a allowlist estrita antes de armazenar, sem aceitar a caixa opaca na saída.
- Centraliza upload de vídeos/imagens em Produtos e Posts num pipeline seguro, preservando limites e validações de extensão/MIME.
- Editor de Produtos apresenta sombra e skeleton de mídia, miniaturas com fallback e círculo com porcentagem real de bytes enviados; após 100%, exibe processamento sem simular progresso do servidor, com suporte mobile e movimento reduzido.
- Adiciona testes de regressão API e frontend. [Contrato técnico e matriz de aceite](docs/UPLOAD-MP4-PROGRESSO-20261108.md). Rafa **homologou na staging** o upload do MP4 e confirmou o download da imagem da Shopee funcionando, autorizando expressamente o PATCH e a promoção à `main` em 08/11/2026.
- Evidência da implementação em staging: [PR #360](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/360) CI #1156 SUCCESS, merge `1489aea4649be85a25eb1571a6baf0575ff8348d`, Render staging `dep-dbodr38473hc73ah2u00` LIVE, endpoints saudáveis; [Vault PR #84](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/pull/84) documentou a etapa. A nova versão PATCH está registrada antes da promoção e será verificada com CI/SemVer/deploy de produção. Nenhuma migration, cron, gateway ou postagem externa.

### Docs — Reconciliação da release 3.6.0 depois do deploy de produção (08/11/2026; sem novo bump)

- Após merge e saúde da produção, atualizados README, AGENTS, Guia Mestre, regras, arquitetura, produto, UX, TASK, contrato e Vault para refletir o estado real 3.6.0 e preservar limites de QA. Registro [RELEASE-3.6.0-20261108](docs/RELEASE-3.6.0-20261108.md). Somente documentação; `VERSION=3.6.0` permanece.

## [3.6.0] - 2026-11-08

### Added / Fixed — Descrição do catálogo em posts/campanhas e download da imagem Shopee (MINOR, 08/11/2026)

- Produtos: botão para baixar a imagem principal Shopee diretamente do card expandido, com rota autenticada e escopo de conta, validação estrita do CDN, sanitização, limite de tamanho, quota distribuída e erro apresentado na interface.
- Listas: a API inclui `description` dos produtos vinculados. Uma nova campanha inicia a cópia de cada item com a descrição realmente salva em Produtos; rascunhos previamente editados mantêm suas próprias cópias.
- Criar POST: publicação imediata e recorrente herdam a descrição do produto escolhido, salvo quando já há texto próprio. Edição manual e IA na publicação não mudam `products.description`.
- Campanhas: geração de descrição IA por produto/persona e botão explícito para restaurar a descrição do catálogo, sem gravar no produto-base e sem sobrescrever edição concorrente durante a geração.
- Sem migration, mudança de RLS, scheduler, `pg_cron`, `pg_net`, chaves ou publicação real. Documentação em [contrato de herança](docs/PRODUTOS-DESCRICOES-CAMPANHAS-20261108.md). Release compatível **3.5.0 → 3.6.0**, aprovada por Rafa para promoção à produção em 08/11/2026; versionamento formalizado primeiro na `staging`.
- **Evidência staging 08/11:** [PR #354](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/354), [CI #1144 SUCCESS](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42514522631), merge `dd83a36c`, Render `dep-dbocnrp42hec73d9crm0` LIVE, `/health` e `/api/health/ready` OK. QA autenticada de Produto/Post/Campanha ainda pendente; `main` intocada.
- **Promoção posterior autorizada 08/11:** PR #356 CI #1148 SUCCESS e staging `91926bbf` LIVE; [PR #357](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/357) CI #1150 e SemVer #8 SUCCESS → `main` SHA `699e81bd18e2b12fc3824f914045627a45844cc2`, CI push #1151 SUCCESS, Render produção `dep-dbod0q7b9u1s73dhci7g` LIVE; health/ready OK e login 3.6.0. A nota de `main intocada` da linha anterior descreve a etapa anterior do processo, não o estado atual. [Fechamento](docs/RELEASE-3.6.0-20261108.md).

### Docs — Fechamento confirmado 3.5.0 e checklist recorrente de segurança (07/11/2026)

- Após CI/SemVer, staging e `main` foram validadas em Render LIVE na versão 3.5.0; evidências documentadas em `docs/RELEASE-3.5.0-20261107.md`, sem nova alteração operacional.
- Adicionados `docs/SEGURANCA-VARREDURA-CHECKLIST.md` (rotina permanente de revisão de segredos, RLS, auth, IDOR, rate limits, ADMIN e injeção/IA) e `docs/SEGURANCA-AUDITORIA-20261107.md` (achados classificados, limites da prova e plano de mitigação; nenhuma correção de código/banco nesta etapa).
- Atualizados Guia Mestre, regras, arquitetura, TASK e espelho do Vault; mudança **somente documental**, sem bump além da release 3.5.0 já implantada.

## [3.5.0] - 2026-11-07

### Added — Máscaras telefônicas com seleção de DDI (MINOR candidata 3.5.0, 07/11/2026)

- `/profiles`, apenas no formulário do titular: **Celular** e **Telefone de contato** passam a ter seletor acessível de país/DDI ao lado do número, com máscaras progressivas por país (Brasil, EUA/Canadá, Portugal e outros DDIs disponíveis) em desktop e celular.
- Novo valor de telefone usa formato internacional `+DDI+número` (E.164); a API normaliza e valida comprimento e mantém validação brasileira de DDD/nono dígito. Números brasileiros legados sem `+55` continuam aceitos e exibidos com máscara nacional, sem migração destrutiva.
- Catálogo local de DDIs sem serviço externo ou dependência nova; trocar de país limpa o número para evitar associar por engano um telefone de outro país. Sem alteração de outros campos, perfis secundários, Supabase, gateway, cron ou `main`. `VERSION=3.4.0` permanece até release aprovada.

### Changed — Data de nascimento, CPF formatado e avisos acima do perfil (PATCH da candidata 3.5.0, 07/11/2026)

- `/profiles`: o campo opcional **Idade** virou **Data de nascimento**, com calendário nativo para dia, mês e ano e persistência de data exata; a coluna legada `age` permanece para compatibilidade, sem fabricar uma data para idades anteriores.
- O CPF recebe automaticamente a máscara `000.000.000-00` durante a digitação, mantendo validação dos dígitos e armazenamento cifrado já existentes.
- Cota compacta e mensagens explicativas/do estado cadastral passam a aparecer organizadas **acima** do card principal. O formulário editável e os retornos da ação de salvar continuam no card; a coluna de perfis secundários, menus e responsividade não mudam.
- Migração **094** adiciona `birth_date DATE NULL` apenas à tabela protegida da conta no Supabase compartilhado, sem alterar RLS/grants. Apenas `staging`; `VERSION=3.4.0` e `main` preservadas, sem gateway, cron ou alterações nos outros campos.

### Changed — Cards de perfis lado a lado em telas grandes (PATCH da candidata 3.5.0, 07/11/2026)

- `/profiles`: quando houver perfis adicionais e largura de tela suficiente (a partir de 1000px), card **principal à esquerda** e perfis **secundários em coluna única à direita**, um abaixo do outro, alinhados ao topo. Sem perfis adicionais, o card principal ocupa toda a largura disponível.
- Em telas menores a grade passa para uma coluna, com perfil principal primeiro e adicionais abaixo; esqueleto de carregamento segue o mesmo desenho. Preservados formulário, cota, foto/nome, menus, seleção e isolamento dos dados.
- Mudança exclusivamente de layout React/CSS e regressão de responsividade. Sem banco, APIs, gateway, planos, cron, serviços de produção ou `main`. `VERSION=3.4.0` preservada, acumulada na candidata `3.5.0`.

### Fixed — Formulário cadastral invisível no primeiro acesso (PATCH da candidata 3.5.0, 07/11/2026)

- Corrigido **HTTP 500 em `GET /users/me/identity`** para contas antigas ainda sem registro em `account_billing_identity`: `maybe_single()` da biblioteca Supabase pode retornar `None` quando não há linha. O endpoint agora devolve os campos vazios e a prontidão de compra, sem tratar a ausência de cadastro como falha.
- Corrigido também o **primeiro `PUT /users/me/identity`**: a verificação de existência aceita o mesmo retorno `None` e cria a linha do titular; edições posteriores continuam preservando o CPF cifrado.
- O formulário completo fica **sempre renderizado dentro do card principal** (nome, CPF, e-mail, celular, idade, recuperação, telefone, endereço completo e CEP). Enquanto a leitura falhar por outra razão, os campos permanecem visíveis, porém desabilitados para impedir sobrescrever dados já persistidos; há opção de tentar novamente. Regressões API/frontend adicionadas.
- Sem DDL, mudança de cota/planos, cobrança, cron, publicação ou alteração de `main`. `VERSION=3.4.0` segue até aprovação de Rafa; staging candidata `3.5.0`.

### Changed — Dados da conta integrados ao card principal (PATCH da candidata 3.5.0, 07/11/2026)

- `/profiles`: o formulário cadastral saiu da área independente da página e passou a viver **dentro do card do perfil principal**, junto à sua foto e nome. A cota compacta e o upgrade condicional também ficam nesse card; os perfis secundários permanecem apenas foto/nome, com menu de ações.
- Mantidos campos editáveis e estado de prontidão de compra diretamente no card principal, sem duplicar dados por perfil. E-mail de autenticação continua apenas leitura até existir fluxo de troca com verificação de posse; CPF é protegido e não reexibido.
- Sem mudança de API, payload, Supabase, migration, gateway, cron, publicação ou `main`. UI responsiva e testes de separação principal/secundário atualizados. `VERSION=3.4.0` preservada; correção acumulada na candidata 3.5.0.
- [PR #344](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/344) merged apenas em staging `e1f61a4`; [CI #1124](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42419595799) SUCCESS e Render `dep-dbnq5pcs728c739ha80g` LIVE. Documentação final sincronizada no Vault; falta homologação visual de Rafa.

### Changed — Perfis com identificação somente por nome/foto (PATCH da candidata 3.5.0, 07/11/2026)

- `/profiles`: retirada a etiqueta do plano ao lado da cota; mantidos **Cota de perfis** e upgrade somente quando disponível. A tag animada do cabeçalho global não foi alterada.
- Cards de perfis exibem **somente foto e nome**, com seleção pelo card e gerenciamento no menu de opções; sem e-mail, telefone, endereço, status e etiquetas de função/plano duplicadas.
- Criar/editar perfil pede **nome e foto opcional**, sem dados pessoais; backend aceita perfis novos com e-mail nulo no schema existente e edição parcial preserva contatos legados. `GET /profiles` retorna apenas campos necessários aos cards (não reenvia contatos legados). Foto é enviada após criação/edição, sem repetir a criação em caso de falha de upload.
- Nenhuma migration, exclusão de dados legados, alteração de planos, gateway, cron ou `main`. Documentação/testes atualizados; versão oficial `3.4.0`, candidata `3.5.0`.

### Added / Changed — Identidade cadastral por conta e perfil compacto (MINOR candidata 3.5.0, 07/11/2026)

- `/profiles`: banner de plano substituído por cota de perfis e botão de upgrade apenas para Free/Pro (a etiqueta inicialmente incluída foi removida no ajuste de UX posterior). Novo formulário de dados cadastrais do titular da conta, sem misturar CPF e contato com perfis sociais.
- Novo cadastro Supabase e conclusão Google passam a exigir **nome completo e CPF válidos**; e-mail/senha permanecem obrigatórios no cadastro por e-mail. O username técnico é gerado pelo servidor. Celular passa a ser obrigatório **para futura contratação**; idade, e-mail alternativo, telefone, endereço e CEP continuam opcionais.
- Nova migration aditiva `093_account_billing_identity.sql`: CPF cifrado, HMAC para deduplicação, tabela vinculada à conta, RLS bloqueando anon/authenticated e integração com pending registrations. Endpoints autenticados `/users/me/identity` e `/users/me/purchase-readiness`; nenhum checkout ou cobrança foi criado. Privacidade/dados coletados e testes atualizados. `VERSION=3.4.0` preservada; produção `main` requer aprovação de Rafa. [Contrato](docs/CADASTRO-IDENTIDADE-PLANOS-20261107.md).

### Removed — Sondas manuais de coleta no painel Análises (PATCH da candidata 3.5.0, 07/11/2026)

- Retirados os três botões **Verificar coleta de Threads/Facebook/Instagram** do rodapé de Análises para todos os perfis, inclusive ADMIN. Eliminados os handlers, estados, mensagens, importações e estilos responsivos exclusivos.
- A rota órfã de diagnóstico **POST /analytics/probe/{network}** também foi descontinuada; testes agora confirmam HTTP 404 para os caminhos antigos e validam os insights oficiais pelo módulo compartilhado de posts. Sem remover a coleta automática, a atualização manual, os indicadores, as nove redes ou as métricas.
- Guia Mestre, plano, testes históricos e TASK reconciliados. Nenhuma migração, ação em banco, cron ou produção. `VERSION=3.4.0` mantida; PATCH incluído na release candidata `3.5.0`, main só após aprovação.


### Changed — Ajuste de título do painel de integrações (PATCH, 07/11/2026)

- Alterado somente o título visível do painel de integrações de **Situação das nove redes** para **Situação das redes**; todas as nove plataformas, métricas e estados de conexão continuam exibidos. Sem mudança de lógica, banco, cron ou produção. Mantido `VERSION=3.4.0` (candidata 3.5.0).


### Changed — Análises sem tabelas redundantes (PATCH da candidata 3.5.0, 07/11/2026)

- Retiradas exclusivamente as duas listagens extensas **Detalhamento por rede** e **Desempenho por publicação**, incluindo versões para desktop/mobile. Permanecem intactos os seis indicadores, os seis painéis de gráficos, filtros e cota manual.
- Dados úteis antes exclusivos das tabelas passaram aos próprios painéis: visualizações e interações oficiais por plataforma nos cards de **Situação das nove redes**; data, rede, estado de coleta, visualizações e interações nos itens de **Publicações em destaque**. Publicações sem visualizações oficiais são exibidas após as mensuradas (—, nunca zero presumido).
- Sem mudança nas APIs, no Supabase, nos agendamentos ou em produção. `VERSION=3.4.0` permanece; lançamento candidato `3.5.0` depende de aprovação de Rafa. Teste de regressão das métricas, nove redes e ausência de tabelas.


### Fixed — Preservação das nove redes no filtro e detalhamento de Análises (PATCH da candidata 3.5.0, 07/11/2026)

- Corrigida regressão detectada na QA autenticada após PR #337: restauradas as nove opções em **Rede**, as nove linhas informativas em **Detalhamento por rede** e o estado explícito de integração pendente ao escolher Kwai/Shopee Vídeo/Telegram/WhatsApp. Nenhuma consulta é enviada a endpoints ainda não suportados. Teste de contrato ampliado.

### Added / Changed — Análises diversas e limite de 10 atualizações (MINOR candidata 3.5.0, 07/11/2026)

- Página **Análise de redes** reorganizada com seis KPIs distintos e seis painéis (linha temporal, comparação por rede, composição de engajamento, dias da semana, ranking de posts e matriz das nove integrações). Dados só de posts confirmados pelo Auto Orbital; ausência de insight exibida como indisponível, nunca zero inventado.
- Atualização manual em **Todos os perfis** e perfis individuais; **10 atualizações válidas por conta por dia civil de Brasília**, todos os planos, conferidas por RPC atômica e RLS no Supabase. ADMIN ilimitado; automático 24 h não consome cota. Exibir saldo, desabilitar botão ao esgotar e rejeitar HTTP 429 no servidor. Tentativa sob cooldown não consome cota.
- Migração aditiva `092_analytics_manual_refresh_quota.sql` e rotas autenticadas `GET /analytics/refresh/quota`, `POST /analytics/refresh`. Nenhum novo cron, nenhum dado de perfil geral convertido em métrica de post; não alterar `main` sem aprovação. [Contrato](docs/ANALISE-REDES-DASHBOARD-COTA-20261107.md).

### Changed — Redes compactas também na Publicação única (PATCH incluído na candidata 3.5.0, 07/11/2026)

- `/posts/criar` → **Publicação única** agora apresenta, no mesmo local acima dos produtos, todas as nove redes sociais do catálogo em linha compacta com apenas checkbox e nome; sem logos, cartões ou bordas.
- **Campanha por lista** mantém a escolha por produto, usando o mesmo componente compartilhado. Redes desconectadas, sem suporte ou planejadas permanecem apagadas e bloqueadas; selecionar/desmarcar preserva as validações, e posts existentes continuam somente leitura.
- Alteração de interface e testes frontend; não altera publicação, credenciais, banco, cron, produção ou `main`. `VERSION=3.4.0` permanece, candidata `3.5.0` aguardando homologação.

### Changed — Redes por caixas na campanha por lista (PATCH incluído na candidata 3.5.0, 07/11/2026)

- `/posts/criar` → Campanha por lista mostra nove redes sociais exclusivamente dentro de **Preparar** de cada produto, com checkbox + nome, sem logo, sem cartão ou seletor global. Só redes com publicação implementada e conexão OAuth testada (`state=ok`) são marcáveis; canais planejados ou desconectados ficam apagados e bloqueados.
- Cada produto mantém sua seleção independente e seus textos próprios. Uma rede antiga desconectada pode ser desmarcada, nunca marcada novamente. Credenciais no Criar POST são consultadas por usuário e perfil para evitar cruzamento de estados.
- A ativação de campanhas continua verificando OAuth em tempo real no servidor; nenhum job, Supabase, cron, `pg_net`, token, schema ou produção alterado. `VERSION=3.4.0` mantida; `main` depende de aprovação expressa.

### Docs — Estado de homologação Shopee Vídeo em staging (07/11/2026)

- Guia Mestre, AGENTS e TASK alinhados à PR #331, CI #1089, migration 091, Render staging LIVE e pendências de callback/OAuth real; nenhuma alteração de código, banco, cron, `pg_net`, `main` ou `VERSION=3.4.0` nesta atualização documental.


### Added — OAuth Shopee Vídeo para afiliados (MINOR candidata 3.5.0, 07/11/2026)

- Categoria oficial `Shopee Video Management` também atende criadores afiliados; integração isolada da Affiliate GraphQL com consentimento `auth_type=user`, assinatura HMAC-SHA256, troca e renovação de tokens, cookie de `state` assinado e proteção por perfil.
- ADMIN pode configurar Partner ID/Key global com criptografia e isolamento por ambiente; usuário autoriza e desconecta somente a própria conta. Migration 091 aditiva com RLS e tokens cifrados.
- `POST /shopee-video/preview` valida metadados e vínculos de produtos do perfil sem enviar conteúdo. Publicação real e jobs continuam **desativados** até validação do upload multipart, consentimento e homologação da Shopee. Sem mudança nos cron/filas existentes, Supabase em produção ou `main` nesta branch.
- Callback deve ser cadastrado em Shopee e configurado via `SHOPEE_VIDEO_CALLBACK_URL` específico de cada host. `VERSION=3.4.0` preservada até aprovação de release.
- Contrato de rollout, documentação oficial e critérios de homologação: [SHOPEE-VIDEO-OAUTH-AFILIADOS-20261107](docs/SHOPEE-VIDEO-OAUTH-AFILIADOS-20261107.md).


### Docs — Motivo da rejeição Shopee, perfil verificado e pausa (07/11/2026)

- Acrescentadas evidências do console: notificação de perfil **aprovado em 03/11/2026**, `My Tasks` com **0** obrigatórias/recomendadas em andamento e rejeição `Penetration Test Report` **Case ID 1750** (04/11), porque era somente revisão de código/documento, sem testes ativos nem screenshots/requests/saídas dos achados R-01...R-07.
- Atualizado [roteiro de cadastro](docs/SHOPEE-OPEN-PLATFORM-CADASTRO-20261107.md), TASK, Guia Mestre e Vault. Guardada **mensagem pronta de suporte, não enviada**, perguntando aplicabilidade do pentest a afiliado BR e modo de regularização. A pedido de Rafa, execução externa **em espera**.
- Somente docs; nenhuma modificação em conta Shopee, ticket, app, serviço, dados, cron, `pg_net`, segredos, `main` ou `VERSION=3.4.0`.

### Docs — Regularização do cadastro Shopee Open Platform (07/11/2026)

- Organizada a sequência definida por Rafa: **rejeitado primeiro** (`Penetration Test Report`, motivo não exibido nas capturas), **pendentes depois** (declaração, capturas, URL e conta de teste não enviados), **app por último** (lista atualmente vazia).
- Documento [SHOPEE-OPEN-PLATFORM-CADASTRO-20261107](docs/SHOPEE-OPEN-PLATFORM-CADASTRO-20261107.md) inclui checklist seguro, pergunta de aplicabilidade de pentest para afiliado brasileiro, encaminhamento de suporte e limites de comprovação. Shopee Vídeo permanece pausada e sem API ativa; não houve reenvio de PDF, abertura de ticket, contratação, app novo ou alteração de dados.
- Apenas documentos, `VERSION=3.4.0` inalterada; banco, scheduler, dois cron, `pg_net`, serviços, `staging` executável e `main` intactos.

### Docs — Shopee Vídeo: contrato para afiliados e autorização (07/11/2026)

- Confirmados nas fontes Shopee Brasil vídeos de 3–60 segundos, até seis produtos vinculados **no vídeo** (URLs em descrições não substituem o vínculo), revisão de relevância e atualização da comissão padrão em 01/07/2026, sem promessa de ganhos.
- Documentada a distinção ainda pendente entre feed de **criadores afiliados** e APIs `Video Management` para **vendedores**. O cliente técnico segue bloqueado; as redes atuais continuam com seleção de um produto e a coleta por vídeo ainda depende de OAuth, ID externo e campos autorizados.
- Somente documentação, sem API externa, UI, DB, cron, scheduler, OAuth, publicação ou alteração de `VERSION=3.4.0`.

### Added — Análises sociais (candidata MINOR 3.5.0, 07/11/2026)

- A página `/analytics` oferece nove redes sociais no seletor Rede, em ordem alfabética PT-BR; nenhuma loja entra nesse catálogo. **Ajuste visual posterior à PR #326:** retirados os cartões de redes acima dos indicadores, por redundância com o seletor.
- O **Detalhamento por rede** passa a listar as nove opções em “Todas”, na tabela desktop e nos cartões de indicadores mobile. Cada rede exibe seu estado; apenas as cinco redes operacionais podem apresentar contagens reais da API, enquanto as quatro futuras mostram traços em vez de zeros artificiais. Selecionar rede não integrada mantém uma linha informativa em vez de esconder a tabela.
- Shopee Vídeo, Telegram, WhatsApp e Kwai aparecem no filtro com informação de integração pendente, sem consultas inválidas ao backend nem números fictícios. Os cinco filtros reconhecidos, gráficos, histórico por perfil e coletor individual Threads não foram alterados.
- Nova [matriz de origem de dados e bloqueios por rede](docs/ANALISE-REDES-COBERTURA-20261107.md). Sem API externa, OAuth, banco, scheduler, `pg_cron`, `pg_net` ou publicadores novos. `VERSION=3.4.0` até release aprovada.

### Changed — Catálogo completo no diagnóstico ADMIN (MINOR candidata 3.5.0, 07/11/2026)

- Abaixo da gestão global de IA/Shopee, o diagnóstico agrupa Lojas e Redes sociais e reaproveita todos os 14 placeholders já presentes em `/credentials`, mais os seis status sociais reais e Shopee Vídeo, totalizando 21 cards pequenos no painel de status.
- Lojas e redes futuras exibem logos locais e estado "Em breve"; não são consideradas conectadas, nem entram no teste geral ou geram chamadas a fornecedores. A UI deriva do catálogo único de plataformas futuras.
- Ajustes de contraste para logos de Mercado Livre/Pró Spin no tema escuro e preenchimento explícito no SVG da Lomadee para evitar dependência de variável CSS não disponível em imagens externas.
- Nenhum endpoint, credencial, armazenamento, scheduler, cron, `pg_net` ou produção alterados. `VERSION=3.4.0` preservada, candidata MINOR `3.5.0` após homologação.

### Changed — Diagnóstico ADMIN compacto e teste consolidado (MINOR candidata 3.5.0, 07/11/2026)

- `/admin/credentials`: cards de IA e Shopee com logos, recolhíveis e lado a lado no desktop (um por linha no celular), preservando gestão completa da chave/modelo/provedor global, opções de salvar/ativar/desconectar.
- Overrides manuais sociais saem da **interface** administrativa; endpoints e credenciais anteriores preservados por compatibilidade. Seis redes passam a aparecer em cards pequenos, ordenados e apenas com situação real/última verificação.
- Um botão `Testar todas as conexões` executa rota ADMIN limitada e isolada: IA ativa, Shopee global e conexões do próprio perfil ADMIN, ignorando configurações ausentes. Registros sanitizados no Render e em `request_logs` (evento explícito de auditoria independente do logging geral); nenhuma chave de cliente é testada ou exposta.
- `VERSION=3.4.0` preservada; candidata MINOR `3.5.0`. Sem DDL, mudança de cron, `pg_net`, scheduler, serviço de publicação ou produção. Contrato [ADMIN-DIAGNOSTICO-CONEXOES-20261107](docs/ADMIN-DIAGNOSTICO-CONEXOES-20261107.md).

### Changed — Credenciais compactas por lojas e redes sociais (MINOR candidata 3.5.0, 07/11/2026)

- `/credentials` recebe abas **Lojas** e **Redes sociais**, cada uma com os grupos existentes **Já credenciados** e **Ainda não cadastrados** e ordenação alfabética PT-BR; cards com logomarcas reais locais, status resumido e corpo fechado inicialmente.
- Correção solicitada por Rafa: **Shopee Vídeo** fica em **Redes sociais**, não em Lojas; a autenticação Shopee Afiliados continua na aba Lojas. Sem habilitar Video Management ou mudar o backend.
- Explicações e links existentes ficam em uma segunda área expandível, independente do card principal. OAuth social, ID de afiliado Shopee, atualização/desconexão e avisos continuam operando como antes. `Testar conexão` sai da tela comum e passa a ficar no painel ADMIN (`Resultado das conexões`).
- 14 cartões de futuras integrações: AliExpress, Amazon, Americanas, Awin, Lomadee, Magalu, Mercado Livre, Natura e Avon, Pró Spin, Rakuten, SHEIN, TerabyteShop, Telegram e WhatsApp. São informativos `Em breve`, sem armazenamento, chamadas de API ou autenticação simulada; Kwai/Shopee Vídeo continuam bloqueados.
- Logos transparentes locais com fontes listadas em [`frontend/public/brand-logos/SOURCES.md`](frontend/public/brand-logos/SOURCES.md); testes Node específicos e gate CI de frontend estendido. `VERSION=3.4.0` permanece; classificada como melhoria compatível para a candidata `3.5.0`. Nenhum banco, cron, scheduler, postagem, pagamentos ou `main` alterado nesta entrega.
- Contrato e QA: [`docs/CREDENCIAIS-COMPACTAS-LOJAS-REDES-20261107.md`](docs/CREDENCIAIS-COMPACTAS-LOJAS-REDES-20261107.md). PR/CI/deploy de staging documentados após conclusão dos gates.
- **Integração verificada em staging 07/11:** [PR #319](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/319), [CI #1060](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42360659833) verde em todos os gates obrigatórios, merge `staging` `a37b9382407e0aa3223d26b5841849c2ba1b27c6`, Render `dep-dbnf4h7b9u1s73ck27hg` LIVE e health/readiness/logos HTTP 200. QA autenticado e `main` aguardam Rafa.

### Added — Shopee Afiliados da plataforma (MINOR candidata 3.5.0, 07/11/2026)

- Consulta de produtos via App ID/Secret global da plataforma, mantido cifrado, testável e gerenciável somente por ADMIN em `/admin/credentials`; `staging` e `production` com registros próprios no Supabase compartilhado.
- Credenciais comuns agora recebem exclusivamente ID numérico de afiliado por conta (ou URL oficial expandida contendo ID). O backend constrói `an_redir` por cliente sem reutilizar `offerLink` ADMIN; atualiza respostas de produtos/listas existentes e snapshots novos de campanhas.
- Nova migration 090 aditiva, com RLS e isolamento por conta; rotas protegidas e testes de regressão, SQL, API e UI. Nenhum cron, pg_net, scheduler ou rede social alterado. **Atribuição comercial real e autorização regional da Shopee precisam de homologação**, não presumidas pelo teste da URL.
- `VERSION=3.4.0` preservada nesta branch de homologação; a candidata `3.5.0` só vira release mediante aprovação de Rafa para `main`. Detalhes e gates no [contrato Shopee](docs/SHOPEE-API-GLOBAL-ID-AFILIADO-20261107.md).

## [3.4.0] - 2026-11-07

### Added — IA custeada pela plataforma (MINOR, autorização de promoção 07/11/2026)

- `POST /posts/generate-copy` usa exclusivamente o provedor ativo da plataforma; `/ai/status` informa somente disponibilidade, sem exigir chave de clientes. Mantém checagem de propriedade e limite atual de 5 gerações/minuto por usuário.
- Gestão Gemini/OpenAI/Anthropic (chave cifrada, modelo, ativação, troca, teste e desconexão) transferida para `/admin/credentials`, com rotas `/admin/ai` protegidas; card removido de `/credentials` para USER e ADMIN.
- Migration **089** aditiva cria tabelas com RLS e grants restritos, isola `staging`/`production` e copia a chave ADMIN existente sem decifrar nem apagar credenciais legadas. Nenhuma mudança em `pg_cron`, `pg_net`, OAuth, pagamentos ou filas.
- Testes novos da API, RLS e frontend; contratos antigos atualizados. Detalhes: [IA-PLATAFORMA-ADMIN-20261107](docs/IA-PLATAFORMA-ADMIN-20261107.md).
- **Promoção efetiva em 07/11/2026:** Rafa autorizou merge integral. PR #311 CI #1043 e #312 CI #1045 entregaram a funcionalidade e sua documentação na staging; PR de release [#313](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/313) CI #1047 SUCCESS, staging `b5bcbc0760af579dc24cd50f9508202e21b92b8b` e Render `dep-dbndesfb9u1s73cinq4g` LIVE. [PR #314](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/314) aprovada na [CI #1049](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42352814892) e [SemVer #4](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42352814886), merge `main` `4ca125faf72f58c7d5c7623fc7b2a8bbb215f1b0`. Render produção `dep-dbndgcnb9u1s73cip6mg` **LIVE**, health+ready 200, zero logs nível error no período pós-deploy; versões 3.4.0 iguais em `main`/`staging`. Migração 089 já aplicada com RLS e isolamento, segredos antigos preservados; dois cron jobs intocados. QA autenticado ADMIN e geração real Gemini não comprovados. Google AI Pro e cobrança Gemini API são separados; monitorar teto de gastos.

## [3.3.0] - 2026-11-07

### Release 3.3.0 — promoção autorizada em 05/11/2026

- Release **MINOR retrocompatível** autorizada por Rafa, consolidando o conteúdo homologado em `staging` após a 3.2.0. A rastreabilidade detalhada de cada item permanece nas seções abaixo e em [docs/RELEASE-3.3.0-20261105.md](docs/RELEASE-3.3.0-20261105.md).
- Inclui: análises somente por post do Auto Orbital (não por perfil externo), seletor todos/um perfil, histórico de Posts paginado, busca contextual e classificação de Listas, personalização e mídia de Produtos, IA de descrição, barras de cotas, comparação de planos, ajuste do criador/campanhas e da etiqueta visual; **Credenciais** ordenadas alfabeticamente e agrupadas por cadastro, com Shopee Vídeo informativo (não conectado).
- Migrations aditivas 087 e 088 já observadas no banco compartilhado; fluxo de agendamento, `pg_net`, dois `pg_cron` e restrições de integração não são modificados pela versão. Integrações Facebook/Instagram desconectadas, X bloqueado e métricas externas indisponíveis não são tratadas como zero.
- **Porta operacional:** a versão de código em `main` e o deploy Render de produção só podem ser declarados após PR de promoção, verificações de CI/saúde e registro de SHA exatos. GitHub Actions recuperado em 07/11: CI #1028, #1030 e #1032 aprovadas em PRs para staging; os resultados antigos que falharam antes dos steps são históricos.
- **Promoção efetiva em 07/11/2026:** PR de release #303, CI #1035 e merge staging `821a16a`; Render staging `dep-dbnca34s728c73934u0g` LIVE e endpoints de saúde 200. [PR #308](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/308) passou CI #1037 e gate SemVer #2, promovida em merge normal para `main` SHA `1cde5216c385985a1360dc9d730286e40faab283`. CI push #1038 e CD produção #169 SUCCESS; Render produção `dep-dbncbp0473hc739ghhpg` LIVE, `/health` e `/api/health/ready` HTTP 200, scheduler iniciado, sem logs de nível error na janela analisada. `VERSION=3.3.0` em ambas as branches. Sem testes de postagem/pagamento real nem QA autenticado dos grupos nesta etapa.


### Changed — Credenciais separadas por cadastro (branch, 07/11/2026)

- A página `/credentials` agora distribui os nove cards em seções **Já credenciados** e **Ainda não cadastrados**, com títulos, contagens, mensagens de vazio e ordem alfabética PT-BR por seção, preservando cartões, ações e layout responsivo.
- Critério de grupo: `connected` da API, inclusive quando o teste está vencido/amarelo; IA cadastrada se qualquer provedor tem chave salva; Shopee Vídeo permanece pendente e sem integração. Query de IA compartilhada, estado de erro com retentativa, mudança automática de grupo após salvar/desconectar, sem expor segredo.
- A PR #304 passou na CI real [#1030](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42345936793) e foi integrada à staging no SHA `4d483d2`; a [PR #306](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/306) foi reconciliada com essa base, com cobertura incluída na CI. Os seis testes específicos passaram anteriormente; a validação remota deste merge e o QA autenticado ainda são gates da #306. O incidente [#305](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/issues/305) é histórico.
- Classificação **MINOR candidata 3.3.0**; `VERSION=3.2.0` preservado. Sem alteração de API/backend, banco, migrations, cron, pg_net, flags, pagamentos ou produção.

### Fixed — GitHub Actions e contratos de frontend (07/11/2026)

- GitHub Actions voltou a iniciar jobs após o repositório se tornar público; o bloqueio observado em 05–07/11 permanece registrado como histórico, **não é o estado atual**. A primeira reexecução real da CI da PR #304 identificou quatro testes frontend desatualizados.
- Contratos atualizados para a etiqueta de plano com exposição de 24 px, busca contextual da TopBar, hook de perfil no resumo de plano, e controles de IA reutilizados no criador de posts. Nenhum comportamento comercial, mídia ou produção foi alterado para satisfazer testes antigos.
- Segunda etapa da CI identificou o teste de paginação importando diretamente `.ts` em Node 20 (`ERR_UNKNOWN_FILE_EXTENSION`). O teste agora transpila o módulo TypeScript puro em memória, sem modificar o código do produto ou exigir Node 24.
- A branch de credenciais mantém `VERSION=3.2.0`; a funcionalidade compatível compõe a candidata **MINOR 3.3.0**. A PR técnica #307 foi aprovada pela CI #1028 e integrada primeiro à staging; a PR de UI deve confirmar CI própria e homologação antes de qualquer promoção.
- O deploy de staging dessa base técnica ficou **LIVE** no Render (`dep-dbnc0jh42hec73c9v66g`, SHA `48b9c34`), com `GET /health` retornando HTTP 200 e `status=ok`. A integração visual depende de CI no seu SHA final.

### Changed — Credenciais (staging, 05/11/2026)

- Cards de `/credentials` exibidos em ordem alfabética PT-BR: Facebook, Instagram, Inteligência Artificial, Kwai, Shopee, Shopee Vídeo, Threads, TikTok e X (Twitter), preservando estado, teste, OAuth, formulários, responsividade e recolhimento.
- Adicionado card recolhível **Shopee Vídeo** com aviso de aprovação oficial pendente e ação de conexão desabilitada. Nenhuma credencial Affiliate é reutilizada, nenhuma nova API/OAuth ou publicação foi habilitada. UI informativa, sem alteração do backend, Supabase, cron ou flags. Testes Node específicos de ordem e bloqueio adicionados; a indisponibilidade inicial de CI foi superada em 07/11 e as aprovações devem usar as novas execuções reais.


### Fixed — Regressões de contratos Python após retorno do Actions (07/11/2026)

- A CI real da PR #304 identificou **9 falhas em 1.264 testes de API** (run #1026), em testes historicamente acoplados a comportamentos removidos/atualizados: edição de preço Shopee, retorno do UPDATE e limpeza da mídia antes da exclusão; consulta geral de insights de Página Facebook; rejeição de contagens ambíguas de um post Threads.
- Contratos de teste alinhados à regra atual de produto: **preço importado é imutável** (422), nome/copy podem ser editados, exclusão remove mídia e gera auditoria; métricas de Análises só vêm de posts realmente publicados, com identidade de job e ID externo, sem métrica geral de Página. Respostas inválidas não são convertidas em zero.
- Branch de correção `fix/ci-contratos-api-20261107` destinada primeiro a `staging`. Mudança de testes, documentação e remoção de CSS sem uso; `VERSION=3.2.0` mantida, release candidata `3.3.0` continua MINOR. Nenhuma rota, lógica de backend, banco, produção ou cron foi modificada.
- Gate CSP: removidos 14 seletores gerados sem referência após as mudanças em Analytics/Produtos; o teste agora exige correspondência exata entre classes JSX e regras CSS, com limite mínimo histórico reajustado. Testes de segurança web **27/27 PASS** localmente; esta limpeza CSS não altera classes utilizadas.
- Consolidada na PR técnica a correção dos quatro contratos frontend antigos (resumo de plano, layout, IA e mídia) e o teste de paginação compatível com Node 20, anteriormente preparados na PR #304. Isso permite que a branch de manutenção passe a CI independentemente da funcionalidade de credenciais.
- Validação local completa: **API 1.264/1.264**, scheduler **208 PASS + 1 XFAIL**, banco **4/4**, SemVer **5/5** e web/CSP **27/27**, com Python 3.12 e dependências de teste instaladas; GitHub ainda deve confirmar Python 3.13.

### Fixed — Analytics por publicação (staging, 05/11/2026)

- Impedida a coleta de visualizações gerais de perfil Threads, Páginas Facebook e alcance de conta Instagram para a tela de Análises. As métricas só são agregadas de jobs `succeeded` com ID externo, usando fonte oficial **individual da publicação** e deduplicando `(network,external_id)`; o histórico e os KPIs de envios permanecem preservados.
- Introduzidos cache SQL aditivo `publication_insights` (migration 088), coleta individual Threads e ranking `/analytics/posts` com prévia e métricas lifetime por post. Indisponíveis ficam `—`; Facebook/Instagram desconectados e X/TikTok sem fonte validada não recebem números inventados. O filtro de dias seleciona quando o post foi publicado, não o período exato das visualizações.
- Mantidos `VERSION=3.2.0`, main, Supabase crons, pg_net e rotinas de publicação. PRs de staging [#300](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/300) e [#301](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/301), Render final `dep-dbm37g67bikc73egaugg` **live** no SHA `58c5d7a`. QA autenticado: um post Threads confirmado retornou **0 views, 0 likes/replies/reposts**; 14 views gerais da conta ficaram fora. Facebook e Instagram não conectadas; 2 crons inalterados. CI `41988037724` falhou antes dos passos; pytest integral no CI ainda sem execução.

### Added
- **Análises — seletor por perfil (staging LIVE, 05/11/2026):** opção “Todos os perfis” (contagens agregadas da conta, histórico arquivado/legado) e escolha individual sem alterar perfil ativo; preservados período/rede, KPIs, gráficos e detalhamento. API valida pertencimento e compatibilidade, evita dupla contagem de insights oficiais; refresh/probe individuais. PR #298, squash SHA `d588eb1`, Render `dep-dbm27ne8bjmc739fcfag` live. Testes locais de contrato 3/3 e sintaxe Python aprovados; CI GitHub #41981263248 falhou antes de iniciar steps, pendentes pytest/tsc e homologação autenticada. Sem banco/cron/main/produção; MINOR candidata `3.3.0`, `VERSION=3.2.0`.
- **Criar POST — cotas e fluxo linear da campanha (staging, 05/11/2026):** publicação única e campanha exibem barra compacta de limites no lugar dos painéis de plano. CTA para planos só em Free/Pro; oculto em Premium/ADMIN. Configuração da campanha agora precede prévia, salvamento, ativação e acompanhamento/homologação (etapas 01–06). Preservadas ações de rascunhos, mídia, publicação e histórico, com atalho para salvar antes de anexar. Testes unitários locais 5/5; sem alteração de APIs, banco ou cron. MINOR candidata 3.3.0, `VERSION=3.2.0` em staging.
- **Histórico de Posts paginado (staging, 05/11/2026):** exibe até 15 publicações por página e um rodapé discreto com setas anterior/próxima e número da página. Reaproveita a busca contextual existente, pagina resultados filtrados, mantém cursor da API para páginas antigas e reinicia na primeira página ao mudar busca/perfil. Lotes de 90 registros (múltiplo de 15) evitam páginas visuais incompletas temporárias e reduzem requisições. Testes de bordas, busca e navegação adicionados ao CI; nenhuma alteração no scheduler, Supabase ou regras de publicação.
- **Ordenação completa de Listas (staging):** seletor com 10 opções (nome A→Z/Z→A, criação recente/antiga, maior/menor número de produtos, edição recente/antiga e mais/menos campanhas efetivamente ativadas). O filtro contextual permanece aplicado antes de ordenar. O módulo puro `frontend/src/lib/listSorting.ts` define comparadores com desempate determinístico e fallback de `updated_at` para `created_at`; preferência salva localmente. `GET /lists/usage`, autenticado e restrito a `user_id`/`profile_id`, conta uma utilização por campanha com `activated_at` preenchido em `campaign_reservations_f4e`; a consulta é sob demanda, paginada, somente leitura, sem expor copy/mídia, sem migração. MINOR compatível incluída na candidata 3.3.0; `VERSION` permanece 3.2.0 na staging.
- **Busca contextual compartilhada por página (staging):** a TopBar passa a pesquisar em `/lists` de verdade, encontrando listas pelo nome e pelos produtos contidos nelas (até 100 listas por requisição, cobrindo as cotas comerciais). O módulo único `frontend/src/lib/pageSearch.ts` centraliza normalização PT-BR, sinônimos contextuais e resolução da rota para Listas/Posts; o seletor de produtos no modal de Listas também reaproveita a regra. Posts ganha equivalências práticas sem perder filtro por texto/rede/data. A TopBar só aparece em páginas com pesquisa funcional (Meus Produtos, Posts e Listas); Pesquisa Avançada mantém sua busca independente e Dashboard permanece sem campo. Produtos salvos continuam no backend seguro `api/product_search.py` para paginação e isolamento de conta. Recurso compatível **MINOR** absorvido na candidata `3.3.0`, mantendo `VERSION=3.2.0` em staging; sem banco/cron/integração paga.
- **Produtos — visualização da personalização salva no card (staging):** no card expandido de Meus Produtos, bloco somente leitura mostra descrição persistida e miniaturas das mídias adicionais, com modal de imagem ampliada/player de vídeo e estados vazio/carregando/erro. Busca privada de mídia apenas ao expandir, usando endpoint/cache existentes; sem impacto comercial, backend, schema ou publicação. Funcionalidade compatível MINOR absorvida na candidata 3.3.0, mantendo VERSION=3.2.0 até release.
- **Produtos — Gemini no editor (staging):** botão visível de seleção de imagens/vídeos e reaproveitamento do controle de tom e geração de IA de Criar Post (Casual, Profissional, Divertido, Persuasivo). `POST /posts/generate-copy` recebe `description_only` e usa a chave Gemini do usuário para sugerir uma descrição sem links e até 280 caracteres ponderados; usuário revisa e salva manualmente. Mesmos guardas de login, propriedade, rate limit e credenciais. Sem migrations, Storage novo, cron ou mudança no main. Incluído na funcionalidade compatível MINOR candidata à 3.3.0; VERSION permanece 3.2.0 em staging.
- **Produtos — personalização segura (staging):** edição de produto salvo limitada a nome e descrição curta (até 280 caracteres ponderados na rede mais restritiva, sem URLs). ID Shopee, URL original, comissão, link afiliado, preços e URL da imagem Shopee permanecem imutáveis no backend e na UI. Galeria privada permanente com até cinco imagens e dois vídeos MP4 adicionais por produto, com upload de PC/celular, pré-visualização autorizada e remoção individual; Storage existente, sanitização e reserva global de capacidade. Migração SQL aditiva 087, compartilhada entre staging/main e sem interferência em cron, filas ou publicadores. Funcionalidade compatível **MINOR**, candidata ao próximo `3.3.0` apenas após homologação/aprovação; `VERSION` permanece 3.2.0 durante staging.
- **Produtos — busca por contexto (staging):** a busca dos produtos cadastrados reconhece equivalências práticas (ex.: "lavadora de carro" → lava-jato/WAP/VAP; "quarto" → cama, lençol, colcha e itens relacionados), procurando o nome dos produtos com saneamento de filtros e compatibilidade com o schema legado, limitação de expansão e isolamento da conta. Debounce no campo de busca; a Pesquisa Avançada da Shopee permanece independente.
- **Configurações — planos e limites (staging):** seção `/settings#planos` compara cotas Free, Pro e Premium e concentra as informações de disponibilidade e limites; contratação e mudança de plano continuam indisponíveis.

### Fixed
- **Listas — detalhes sem informações duplicadas (staging):** no card expandido, cabeçalho continua com nome e quantidade; os quatro indicadores superiores continuam com Produtos, Criada em, Atualizada e Valor (mín.). A timeline inferior exibe apenas a relação de produtos e seus valores, removendo as seções repetidas de nome da lista e datas de criação/atualização. Sem alterar dados, cálculos, ações, API ou banco. Correção visual PATCH absorvida na candidata MINOR `3.3.0`; `VERSION=3.2.0` mantida.
- **Listas — banner reduzido à cota (staging):** removido o painel expansivo de plano (etiqueta, avisos e texto de upgrade) em `/lists`, substituído pela mesma barra compacta reutilizável de Produtos. Exibe consumo/limite de listas por perfil; contas sem teto comercial mostram quantidade cadastrada. Free/Pro têm botão “Melhorar plano” para `/settings#planos`; Premium e administrador não exibem CTA. A validação do limite e os dados da API permanecem inalterados. Ajuste PATCH incluído na candidata MINOR `3.3.0`; `VERSION=3.2.0` até a liberação.
- **Produtos — busca do cabeçalho condicionada à aba (staging):** na mesma rota `/products`, a barra de busca global fica visível apenas em **Meus Produtos** e desaparece em **Pesquisa Avançada**, que conserva sua busca própria. O estado da aba é compartilhado pelo layout e pela página com Zustand, inclusive ao restaurar filtros; a busca de Meus Produtos não é apagada ao trocar de aba. Sem alterar outras rotas, API ou dados. Ajuste PATCH na candidata MINOR `3.3.0`; `VERSION=3.2.0` até release.
- **Produtos — organização do card expandido (staging):** preservado o cabeçalho de imagem/nome/ID; abaixo, carrossel responsivo com setas, até três imagens ou vídeos extras visíveis (2/1 em espaços menores), seguido de descrição persistida, links Shopee/afiliado e, por último, os cinco indicadores comerciais. Miniaturas continuam abrindo prévia, mídia privada continua sob demanda, sem alterar API, cálculo ou importação. PATCH visual acumulado na candidata MINOR 3.3.0; VERSION 3.2.0 até aprovação de release.
- **Produtos — remover detalhes comerciais duplicados do card (staging):** indicadores de ID Shopee, preço, comissão, ganho/venda e cadastro permanecem na linha de cards superior; a timeline detalhada foi reduzida a Links (original e afiliado), sem repetir Produto, Preço, Comissão ou Cadastro. A prévia de descrição/mídias permanece abaixo. Correção visual PATCH absorvida na candidata MINOR 3.3.0; VERSION=3.2.0 mantida.
- **Produtos — correção do HTTP 500 ao salvar nome/descrição (staging):** o PUT /products/{id} deixa de chamar .single() em um SyncFilterRequestBuilder do PostgREST (método indisponível para UPDATE). Usa .execute(), trata a lista de linhas retornada e preserva o filtro por conta/ID, validação da copy e imutabilidade comercial. A mídia já salva permanece intocada. Regressão testada com fake sem .single() antes do commit. Correção PATCH agregada à candidata MINOR 3.3.0; sem bump antecipado de VERSION=3.2.0.
- **Produtos — skeleton sem ação fantasma (staging):** retirado o placeholder de botão à direita do cabeçalho durante o carregamento, pois a tela não possui tal ação. Mantidos skeleton de título, filtros e lista, além do cartão de perfil independente na TopBar; correção visual PATCH absorvida na candidata MINOR `3.3.0` (`VERSION=3.2.0` até release aprovada).
- **TopBar — carregamento da identidade/etiqueta (staging):** o cartão de foto/nome mantém altura e largura de referência no skeleton, inclusive no mobile, sem sobrepor Sair/Notificações; a aba do plano só aparece após a resolução de perfil e cota válidos. Nunca exibir o texto provisório “Plano indisponível”. Correção visual PATCH absorvida pela candidata MINOR `3.3.0`; `VERSION=3.2.0` até homologação e aprovação de release.
- **Compilação do editor Gemini (staging):** import da navegação não utilizado removido do compositor após compartilhar o controle de IA; correção de build sem mudança de comportamento.

### Changed
- **TopBar — etiqueta de plano com entrada deslizante (staging, 05/11/2026):** a etiqueta aparece saindo de trás do cartão do perfil (680 ms, easing suave), terminando 24 px exposta no desktop e 19 px no mobile, um pouco menos que antes. A animação começa apenas quando o badge de plano monta, sem animar o skeleton de perfil, e desativa movimento com `prefers-reduced-motion: reduce`. CSS apenas, sem APIs ou permissões. Ajuste visual PATCH absorvido na candidata MINOR 3.3.0; `VERSION=3.2.0` mantida na staging.
- **Produtos — campo de busca único (staging):** removido o input duplicado à direita do título; a busca contextual dos produtos cadastrados passa a usar exclusivamente o campo existente na TopBar, compartilhando o estado e preservando o debounce. Busca dos Posts continua independente, e a Dashboard permanece sem busca. Correção visual/UX compatível (PATCH) incorporada ao candidato MINOR `3.3.0` em homologação; sem alteração antecipada de `VERSION`.
- **Produtos — cota compacta (staging):** remove o cartão amplo com etiqueta de plano repetida e avisos. Mantém somente consumo/limite de produtos da conta e ação "Melhorar plano" para Free/Pro; Premium e Administrador exibem apenas a cota. O cartão de avatar/nome e etiqueta no topo não foi alterado.
- **SemVer pendente:** a busca por contexto constitui funcionalidade compatível nova, classificada **MINOR**. Candidato ao próximo `3.3.0` (absorvendo os ajustes PATCH ainda não lançados); `VERSION` permanece `3.2.0` na staging, conforme `docs/RULES.md`, até homologação e promoção explicitamente aprovada para `main`.

- **Dashboard e identificação no topo (staging):** busca do cabeçalho oculta apenas em `/app`, preservando a busca das demais páginas; cartão de avatar/nome opaco e arredondado em primeiro plano, ampliado para a proporção da referência (70 px de altura, foto de 48 px); segundo cartão da etiqueta dinâmica do plano atrás e parcialmente exposto por baixo do primeiro, alinhado em largura e eixo vertical, sem sobrepor o nome, com ajuste responsivo para celular. Mudança visual compatível de natureza PATCH; combinada à funcionalidade de busca atual, integra o candidato MINOR 3.3.0 após homologação e aprovação da promoção.

## [3.2.0] - 2026-11-04

### Added
- **Dashboard da conta:** contagens de produtos, postagens-raiz, listas e agendamentos somadas por `user_id` em todos os perfis da mesma conta; histórico dos perfis arquivados permanece representado. Painéis de até cinco postagens/atividades recentes; atalhos de produto, post e lista preservam o perfil ativo nas ações.
- **Exclusão segura de perfil:** arquivamento lógico transacional de perfil secundário, sem destruir posts, histórico `succeeded/failed/unknown`, atividades e mídia histórica. Agendamentos, recorrências e campanhas ainda em fila podem ter o despacho cancelado/removido conforme estado; perfil principal protegido.
- **Exclusão integral da conta:** fluxo retomável de banco, Supabase Storage API e Supabase Auth Admin API, com confirmação de identidade, validação de propriedade e finalização exclusivamente depois das etapas externas. Migrações SQL 080–086 no Supabase único compartilhado entre produção/staging; sem criar ambiente novo.
- **Prevenção de regressão SemVer:** workflow `release-semver.yml` barra PR de código/configuração/CI para `main` quando `VERSION` não é incrementado por MAJOR/MINOR/PATCH válido ou falta entrada datada correspondente no `CHANGELOG`. Documentação isolada não força bump.

### Segurança e compatibilidade
- Triggers 085/086 bloqueiam `DELETE` físico legado de perfil/conta e autorizam cascatas somente pela rotina finalizadora transacional; FK 084 impede novos `request_logs` órfãos sem apagar os 1.299 registros legados de origem não auditada.
- Funções e tabelas internas restringidas a `service_role`; contas só podem ser excluídas mediante ação explícita autorizada. As flags `PROFILE_ARCHIVAL_ENABLED` e `ACCOUNT_ERASURE_ENABLED` continuam **desligadas por padrão**; a ativação destrutiva em produção não foi autorizada sem homologação Storage/Auth completa.

### Evidências da base técnica promovida
- Staging: PRs #265–#268; CI #949 aprovado; Render `dep-dblp18mq1p3s738pakkg` LIVE em `7941338`. Promoção para `main`: PR #269, CI #951 aprovado, commit `5b7b040`, Render `dep-dblpjblg1s2s73c32i60` LIVE, scheduler iniciado e API inicializada.
- Supabase compartilhado: migrações 080–086 aplicadas, testes transacionais sintéticos com `ROLLBACK`, sem excluir usuários/perfis reais; dois crons mantidos (`*/12` uptime e `*/2` wake). Nenhuma publicação externa nova, pagamento ou envio automático comprovado nesta release.
- Esta versão **3.2.0** formaliza funcionalidades que já chegaram à produção antes do bump por falha de processo; a promoção do `VERSION` e a confirmação dos deploys 3.2.0 devem ser registradas na entrega desta correção.

> As notas abaixo foram escritas durante a preparação em staging e permanecem como histórico; declarações antigas de "PR em preparação", "main intacta" e "3.1.2 mantida" descrevem momentos anteriores à promoção acima.

### Operação de staging — migração 084 idempotente
- No primeiro deploy do PR #266, o migrador próprio do Flask tentou reaplicar a FK 084 já existente no Supabase (históricos de migração distintos), causando falha de boot de worker apesar do estado Render `LIVE`. Após verificar FK/índice, registrado `084_request_logs_erasure_fk_not_valid.sql` em `public.migrations` sem alterar dados. Redeploy do mesmo commit `5600ab0` ficou `LIVE`, com 080–084 ignoradas como já aplicadas e scheduler inicializado. Hotfix #267 torna a DDL 084 idempotente para impedir nova colisão. Main e crons intactos; VERSION mantida.


### Segurança e retenção de perfis — PR #266 em preparação (schema aplicado, flags OFF)
- Por decisão de Rafa, exclusão de perfil secundário passa a ser arquivamento lógico: conta e histórico de publicações `succeeded/failed/unknown` são preservados; agendamentos/recorrências/campanhas ainda pendentes podem ser cancelados/removidos sem reenvio. Perfil principal só desaparece com a conta.
- Supabase único e compartilhado entre staging/main: migrações `080_profile_archive_history_expand`, `081_account_erasure_atomic_flow`, `082_account_erasure_view_cleanup_fix`, `083_account_erasure_username_logs` e `084_request_logs_erasure_fk_not_valid` **aplicadas em 04/11/2026 por autorização do Rafa**. DDL aditiva, sem exclusão de dados existentes; RPCs exclusivas `service_role` com `anon/authenticated` negadas.
- Conferência após DDL: 4 perfis, 3 agendas, 3 jobs e 5 objetos Storage intactos; nenhum usuário/profil real arquivado/excluído. Testes SQL com dados sintéticos e `ROLLBACK` validaram arquivamento, proteção do principal, idempotência e finalização de conta com remoção de audit/request logs; zero registros de teste residuais.
- Backend na branch: `PROFILE_ARCHIVAL_ENABLED=false` e `ACCOUNT_ERASURE_ENABLED=false` por padrão; proteção de claims/dispatch, cotas e dashboard, e orquestração idempotente de exclusão integral em DB/Storage/Auth com recuperação manual administrativa e senha Auth atual para identidades vinculadas. Código não implantado até revisão/CI/staging.
- Proteção adicional 084: FK `request_logs.user_id → users.id ON DELETE CASCADE NOT VALID`, com índice. Teste transacional comprovou cascata e bloqueio de novos logs com usuário inexistente. Permanecem 1.299 logs **legados órfãos** anteriores à FK, preservados (não removidos sem auditoria de origem).
- Middleware evita regravar log identificável após exclusão concluída; teste de regressão incluído.
- Pendências antes de ativar: CI definitivo e testes de integração/corrida em staging com Storage/Auth e F4E, compatibilidade do main legado, validação da preservação do histórico; main só após aceite do Rafa. **Nenhum pg_cron, pg_net, scheduler ou serviço alterado/desligado**; `VERSION=3.1.2` mantida.

### Fixed — dashboard da conta (staging PR #265, pendente de homologação)
- Dashboard passa a agregar produtos, posts-raiz, listas e agendamentos por `user_id` autenticado, abrangendo todos os perfis da conta e registros históricos com `profile_id NULL`, sem alterar as telas operacionais isoladas por perfil. Painéis de postagens/atividades recentes leem até cinco registros reais e distinguem ausência de dados de falha parcial.
- Ações rápidas direcionam à criação de produto, post e lista sem contornar autorização/limites do plano; cache da visão geral segregado por conta, com revalidação.
- **Limite conhecido:** exclusão física de perfil ainda provoca CASCADE em dados F4E de campanhas; retenção integral após exclusão demanda projeto de arquivamento/soft delete compatível com o Supabase compartilhado. Nenhuma exclusão, DDL, migration, cron, scheduler ou produção nesta correção. `VERSION=3.1.2` mantida até eventual release autorizada.

### Operations / Documentation
- Ajuste explícito de Rafa no Supabase `pg_cron`: `auto-orbital-uptime-sample-v1` de 5 para **12 minutos** (`*/12 * * * *`), `auto-orbital-wake-v1` de publicações mantido intacto em **2 minutos**, `auto-orbital-admin-capacity-v1` desagendado/excluído do registro cron. Verificação confirmou exatamente dois jobs ativos e comandos originais idênticos; nenhuma função/tabela/serviço/campanha modificada. Configuração operacional + documentação; `VERSION=3.1.2` sem bump.

### Documentation
- Retificação baseada em SQL read-only do Supabase: `pg_cron` de publicações já opera com `auto-orbital-wake-v1` a cada dois minutos, função `app_internal.wake_dispatch_if_needed`, `pg_net` e segredos em Vault para wake do Render sob trabalho pendente. Proposta anterior de upgrade Render para sustentar agendamentos foi incorreta e não está autorizada. Obrigatório verificar documentação, código implantado, cron, filas e logs antes de recomendar infraestrutura; distinguir cron SQL, despertar HTTP e envio externo confirmado. Somente docs, sem bump de `VERSION=3.1.2` nem alterações de serviço.

## [3.1.2] - 2026-11-04

### Fixed
- Robustez das consultas GET somente-leitura de consentimento/localização, GPS, preferência regional e origem de aquisição em `/profiles/*`: reconexão/transporte HTTP/2 do Supabase/PostgREST recebe uma única nova tentativa via helper já utilizado em autenticação, fora do event loop; falha persistente devolve HTTP 503 genérico em vez de erro 500. O incidente observado em staging foi `GET /profiles/location-sharing` às 02:19 BRT. Sem retry de PUT/DELETE, sem mutação de banco e sem alterar dados de consentimento. Oito testes de regressão cobrem recuperação e falha segura.

- **Evidência de promoção:** Staging PR #257, CI #901 SUCCESS, merge `4a4b638acbe7ca526f9e80843ced7208fa7ded64`, Render `dep-dblc4hvavr4c73cmm6d0` LIVE, scheduler iniciado, readiness 200. Promoção main PR #258, CI #903 SUCCESS, merge `70025853c2fce6ec82165649a6881a4e3ecd0c38`, Render `dep-dblc6b7b9u1s73b9uch0` LIVE, scheduler iniciado, readiness HTTP 200; Supabase `ACTIVE_HEALTHY`, ambos Render `not_suspended`, versões 3.1.2 em ambas e compare main...staging sem diferenças de arquivos. Worker antigo recebeu SIGTERM **após drain** e serviço permaneceu LIVE. Nenhum banco, post, pagamento, retry de escrita ou pausa programada.

## [3.1.1] - 2026-11-04

### Fixed
- GET `/profiles` (SELECT de perfis) repete uma única vez falhas transitórias de transporte HTTP/2/PostgREST usando o helper de autenticação já validado. Execução fora do event loop; duas falhas retornam HTTP 503 sanitizado, não 500. Sem retry de escrita, mudanças de schema ou reenvio de publicações. Testes de recuperação, isolamento por usuário e falha segura.
- Formalizada política permanente de alta disponibilidade: um Supabase compartilhado, `staging` para desenvolvimento, `main` para clientes, deploy sem pausa intencional, aviso prévio mínimo de 24h para manutenção com interrupção, classificação SemVer antes de iniciar. Infraestrutura Render Free atual pode hibernar e não assegura 24/7; upgrade exige aprovação do proprietário.

- **Evidência de release:** staging PR #253, CI #893 SUCCESS, Render `dep-dblbruk9v7es73cuqgsg` LIVE com scheduler iniciado e health 200; promoção main PR #254, CI #895 SUCCESS, merge `39c0dff6614c2d1a7770d3dfc3c42954028cd97c`, Render `dep-dblbtug473hc73b13in0` LIVE, scheduler iniciado, health HTTP 200. Nenhuma manutenção com parada, mudanças de banco ou publicações externas por este patch. O risco de hibernação Render Free permanece.

## [3.1.0] - 2026-11-04

### F4E — Campanhas integradas (release autorizado)

- Implementação técnica de ponta a ponta integrada e validada em staging: reserva transacional por perfil/rede/dia; proteção e cópia privada de mídia; verificação OAuth; materialização atômica de posts/schedulers/jobs com `publication_origin='campaign'`; executor com origem/autorização/isolamento de ambientes, pausa/retomada/cancelamento/recuperação/histórico; interface PT-BR e guardas de plano/período pago.
- Correções do fluxo legado, isolamento `apscheduler_jobs`/`apscheduler_jobs_staging`, leituras de sessão/perfil resilientes a desconexão HTTP/2 e comportamento fail-closed sem retry de jobs `unknown`.
- Autorização expressa de Rafa em 04/11 para promoção integral `staging → main` pelo [PR #248](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/248); staging SHA `2ae7a395` LIVE com CI #881 SUCCESS. A versão é MINOR compatível sobre 3.0.0.
- **Três pendências mantidas fora do aceite técnico por decisão do proprietário:** teste manual final; gateway de pagamento/cobrança real; comprovação de entregas nas redes sociais. Não confundir código em produção com postagem externa comprovada nem com plano quitado.

### Fechamento da implementação e promoção para main (04/11/2026)

- Merge de reconciliação dos 9 commits exclusivos de `main` em `staging` pelo PR #250 (CI #885 SUCCESS), preservando guards `legacy`/`campaign`, escopo de ambiente e histórico dos dois branches.
- Promoção normal `staging → main` pelo PR #248, merge SHA `5e9cae5137efb6fa8faa1bb765d7a7e1eef6a266`, CI #887 SUCCESS em API, frontend, PostgreSQL isolado e smoke HTTP staging.
- Render staging `dep-dblba7nlk1mc73eolrlg` LIVE com scheduler iniciado; Render produção `dep-dblbb3o473hc73b0gqkg` LIVE com `Scheduler initializing in production`/`Scheduler started`; `/api/health/ready` público respondeu HTTP 200 `status=ok`.
- **Encerramento apenas da implementação técnica da F4E.** Mantidos como pendências de aceite do proprietário: teste manual final, gateway de pagamento/checkout efetivamente quitado e comprovação externa de cada publicação. Nenhum envio nem cobrança executados como parte da promoção.

### Primeira campanha F4E externa ativada, aguardando envio (04/11/2026)

- Após autorização explícita e confirmação específica de Rafa, campanha ADMIN `Homologação de publicação real — 04/11/2026` ativada em **staging** com um produto Air Fryer, uma rede Threads, 1 vaga/ocorrência em 04/11/2026 às 01:45 BRT. O backend exigiu corretamente antecedência mínima de 30 minutos e a janela foi ajustada.
- Reserva `6dfbab2d-cc9f-42fb-9dec-840067017573`: `lifecycle=active`, `dispatch_enabled=true`, `media_verified=true`, `oauth_verified=true`, um asset privado, uma verificação OAuth, um slot; `posts`, `schedulers` e `publish_jobs` materializados com origem positiva `campaign` e agendamento idêntico. Job `pending`, progresso 1 planejado / 0 enviados às 01:10 BRT.
- Agendada checagem automática para 01:55 BRT. Não marcar como entrega externa comprovada antes de ID/resultado remoto e conferência no histórico; `main`/produção ainda não recebeu F4E.

### Homologação pós-CI — PR #245 LIVE e próxima entrega real (04/11/2026)

- [PR #245](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/245) integrado em staging no commit `4a4e0ab` após CI #877 SUCCESS (API Python, frontend e PostgreSQL descartável). Deploy `dep-dblaq067bikc73affoh0` LIVE; logs `Scheduler started` e `Resumed scheduler job processing`, endpoint `/api/health/ready` retornou `status=ok`, sessão ADMIN e UI de posts/campanhas carregaram.
- Preparado no ADMIN um rascunho separado `Homologação de publicação real — 04/11/2026`: um produto Air Fryer, uma rede (Threads), uma ocorrência prevista para 04/11 às 01:10 de Brasília. **Rascunho salvo, ainda não ativado e nenhum envio efetuado**; confirmação específica do disparo externo pendente.
- Uma execução legada Threads em 04/11 00:31 UTC falhou na parte 2/5 com HTTP 403 Meta code 10; há postagens Threads anteriores confirmadas. Diagnóstico de rede/etapa necessário, sem deduzir revogação OAuth. `unknown` permanece sem retry automático.

### Recuperação do scheduler de homologação e correção de perfil HTTP/2 (04/11/2026)

- Reativação autorizada por Rafa: `SCHEDULER_ENABLED=true` apenas no Render `shopee-bot-staging`, deploy `dep-dblakvjm8hqs738nl8h0` LIVE no SHA `e09c9aa`. Logs confirmaram `Scheduler started`; job `publish_queue_recovery` voltou a avançar. `main`/produção permaneceram inalterados.
- As cinco recorrências legadas do staging podem realizar envios reais em seus horários; nenhum `unknown` é reenviado automaticamente. Snapshot após reativação: 12 jobs legados `unknown`, zero campanhas ativas e zero jobs de campanha pendentes/em execução.
- Correção adicional em homologação: resolução de `profile_id` passa a repetir **uma vez** apenas SELECTs com falha `httpx.TransportError`, reaproveitando o helper da autenticação; persistindo a falha, devolve 503 sem perder isolamento ou converter a falha em logout/401. Regressões para token do titular, fallback principal e dois erros consecutivos.
- A implementação F4E do PR #243 e o reparo de sessão do PR #244 estão no staging; o teste de envio de campanha à rede e a promoção controlada para `main` permanecem pendentes. Não confundir deploy LIVE com postagem externa confirmada. `VERSION=3.0.0` até release aprovada.


### Homologação integrada F4E em staging — sessão resiliente (04/11/2026)

- Homologada no navegador com conta ADMIN autenticada a criação de rascunho, ativação controlada, reserva de 1 slot por rede/dia, retenção de 1 mídia, atestado OAuth, materialização de 1 post/job com origem `campaign`, pausa e retomada; evidência na reserva `7805b3a1-a4a5-4d2f-8a82-8fce3389728d` de origem `staging`. Sem postagem externa de teste.
- `SCHEDULER_ENABLED=false` aplicado somente ao serviço de staging, com deploy `dep-dbl9aa0n74is739edteg` live; scheduler de produção intocado e jobs antigos preservados. A reserva de teste foi colocada em pausa após validação.
- Identificado em logs de staging HTTP 500 durante `GET /campaigns/active`: fechamento remoto HTTP/2 (`httpx.RemoteProtocolError`) na consulta de `revoked_sessions` do autenticador. Leituras de identificação de usuário e revogação agora repetem **uma vez** somente erros de transporte, com query reconstruída; se o banco continuar indisponível, retornam 503 sem liberar acesso. Quatro regressões cobrem retry, 401 de sessão revogada e falha fechada após duas tentativas.
- Corrigido o logout indevido quando `/auth/me` responde com 5xx, 429 ou erro de rede: a sessão só é descartada em HTTP 401, com aviso e nova tentativa; a verificação do papel ADMIN segue bloqueando acesso em falha transitória. Corrigida também a indicação de ativação indisponível no compositor, que contradizia o fluxo operacional.
- O comportamento de publicação real Threads/Meta não foi re-testado nesta homologação: um 403 isolado não prova ausência de autorização no perfil. Validar eventual falha pela chamada/etapa/credencial específicas e logs sem expor tokens.
- Alterações limitadas à branch staging; `main` e `VERSION=3.0.0` preservados até promoção formal.

### F4E — implementação integrada de campanhas (PR #243, 03/11/2026)

Implementação em branch de trabalho, **CI #41746477821 aprovada** (API, PostgreSQL 16 isolado e frontend); **migrations 076–079 aplicadas no Supabase compartilhado e registradas no migrador do app**, com cinco índices de FK corrigidos após auditoria de desempenho, com zero slots/posts criados; **sem merge/deploy de staging ou publicação externa** até este registro. A proposta combina as migrations 076–078: cotas de campanha por perfil/dia contabilizadas por rede sob lock de conta; sessão comercial com vigência paga e downgrade pendente aplicado apenas após o término; slots por rede com identidade imutável; mídia retida em prefixo privado por reserva e manifesta no banco; atestados OAuth recentes; materialização atômica de posts, associações de mídia/produto, schedules e publish_jobs com `publication_origin='campaign'` nos três pais. A fila de campanha é separada do legado e revalida OAuth, ambiente, posse, vigência e estado no banco inclusive na última barreira antes da chamada externa; pausa/cancelamento, recuperação de preparação, término desconhecido sem repetição e encerramento com liberação de cota compõem o ciclo. A API e o planejador expõem ativação explícita, limite real do plano, pausa/retomada/cancelamento e progresso/histórico paginado. A CI inclui PostgreSQL 16 descartável e a verificação comum de API/frontend. Não há checkout ou permissão Meta Threads emitidos por essa entrega; o erro 403/código 10 do Threads segue externo. Deploy de staging e homologação integrada são gates separados de merge/main.


### F4E — isolamento real de origem no banco e nos executores (03/11/2026)

Migração aditiva 075 com origem positiva `legacy/campaign` para schedulers e publish_jobs, padrão legado compatível com main antiga e triggers de imutabilidade/consistência de pais. Tentativa de reivindicar ou iniciar envio de job de campanha é rejeitada **pelo PostgreSQL**, inclusive quando um executor antigo ignorar o filtro. Scheduler de staging passa a exigir origem legada em consultas, claim/recovery, reconciliação, cancelamento e barreira antes da API social. Testes unitários e PostgreSQL 16 descartável adicionados. O despacho de campanhas permanece fechado até implantação compatível nos dois ambientes e conclusão de cota por rede, OAuth, mídia e ativação transacional. Nenhuma publicação real, plano ou pagamento é alterado.


### Correção crítica — cron/recovery de posts em staging (03/11/2026)

O claim de publicação separava chave `UUID:YYYY-MM-DDTHH:MM` por dois-pontos e convertia `YYYY-MM-DDTHH` para timestamp inválido, abortando `publish_queue_recovery` e podendo deixar jobs pendentes. Corrigido uso dos 16 caracteres finais do slot nominal, preservando revisão e janela. O recovery agora também encerra `pending` com mais de uma hora como `failed`, sem envio tardio, preservando `unknown`; regressões cobertas por testes unitários e PostgreSQL descartável; nenhum post `unknown` foi repetido, nenhuma configuração OAuth/Threads, banco compartilhado, `main` ou `VERSION=3.0.0` alterados. Logs reais de staging continham `InvalidDatetimeFormat: 2026-11-03T15`. CI e deploy serão declarados separadamente após confirmação.

### F4E-2B4 — origem persistente e rollout seguro (03/11/2026)

Especificação para separar publicações `legacy` e `campaign` por origem positiva, persistente e imutável em agenda/job, vínculo atômico, recusa fail-closed, bloqueio de retry de campanha inerte, compatibilidade main+staging e rollback. A auditoria impede migrar o SQL B3 sem resolver lock de índices, exclusão/LGPD e unicidade de tentativas. Nenhum executor, DDL/Supabase, job, flag, envio, cobrança, e-mail ou `main` alterado. [Plano](docs/superpowers/plans/2026-11-03-f4e2b4-origem-e-rollout-seguro.md); `VERSION=3.0.0`.

### F4E-2B3 — ajuste do harness descartável

Na primeira CI #41723907329, os 9 casos SQL novos passaram individualmente, mas a limpeza foi corretamente interrompida por uma asserção errada do tamanho do nome gerado do banco. Validação substituída por regex exata `f4e2b3_[0-9a-f]{32}` antes do DROP; banco somente local do runner, removido também pelo teardown do serviço Docker. Nova CI necessária para aprovar a suíte completa. Nenhuma alteração de SQL/runtime/Supabase. A barreira de DROP usa exceção explícita, inclusive sob Python otimizado; teste de unicidade isola também o mesmo job em outra ocorrência, sem mascarar a constraint por colisão de ocorrência/rede.

### F4E-2B3 — proposta de identidade dos pais, sem executor (03/11/2026)

A proposta SQL F4E2B2, fora do migrador, acrescenta FKs compostas RESTRICT e índices incluindo PK para impedir troca de identidade dos pais vinculados, com locks ordenados na validação inicial e rede do post conferida. Sem novo grant executável: service_role só lê links. Nova suíte PostgreSQL descartável usa migrations reais dos pais e testa concorrência/REPEATABLE READ, ACL, unicidade, rollback, lifecycle e legado não vinculado; descoberta explícita na CI. Matriz de integração e riscos em `docs/F4E-2B3-PROPOSTA-IDENTIDADE-PAIS-20261103.md`. PR/CI ainda em preparação neste registro; nenhum guard ligado ao executor, Supabase/main/flags/postagem/billing alterados. Pedido de downgrade preserva direitos até fim do período pago. `VERSION=3.0.0`.

### Correção contratual — ciclo pago e e-mails futuros (03/11/2026)

Retificada a regra de downgrade da F4E-2B2: solicitação não restringe plano, campanhas ou quotas antes do vencimento pago. Cancelamento impede renovação futura, preservando acesso quitado; troca/pausa na virada; aviso T−7 e confirmação; upgrade com processamento após pagamento. Requisitos futuros de e-mail transacional/marketing opt-in e ressalva CDC/LGPD registrados. **Somente documentação**, sem checkout/cobrança/SQL/envios/main/alteração de VERSION.


### F4E-2B2 — fechamento de staging (03/11/2026)

PR #234 (`0483b7a`, CI #41713751800) e correção de CI PR #235 (`1363024`, CI #41714645658) integradas somente no staging. O filtro novo executou 15 testes F4E-1 em PostgreSQL isolado e 3 contratos estáticos F4E-2B2; CI de staging #41714932997, smoke #41714932664 e ZAP passivo #41714932408 aprovados. Render `dep-dbl4e317lnhs739rukhg` LIVE nesse SHA. Supabase: zero reservas/ocorrências, proposta de tabela não aplicada. Homologação autenticada pulada; sem envio real, executor F4E, migration, main ou release. `VERSION=3.0.0`.


### F4E-2B2 — ampliação do gate SQL de CI

O workflow de PostgreSQL descartável passa a descobrir também `test_f4e2b2_*.py` além dos testes F4E-1. A primeira CI #41713751800 aprovou scheduler e API, mas não exercitou o novo contrato estático SQL devido ao filtro antigo; esta correção exige nova CI antes de encerrar a homologação. Sem DDL/SQL aplicado ao Supabase ou alteração de `VERSION=3.0.0`.


### F4E-2B2 — identidade persistente inerte e decisão de downgrade (PRE-DEPLOY)

Rafa aprovou pausa integral ao rebaixar Premium→Pro até escolha explícita de até 2 campanhas por perfil, preservando histórico e as demais pausadas. Corrigido o DTO de dispatch para UUID de agenda e fila, INTEGER de post e rede permitida; recusa incondicional mantida. Proposta SQL de vínculo obrigatório, imutável e somente leitura ao service_role foi adicionada apenas em `docs/sql-proposals/`, fora do boot. Testes de contrato adicionados; CI, PR, staging LIVE e validação PostgreSQL ainda não confirmados. Sem alteração do Supabase compartilhado, executores, flags, jobs, publicação, main ou versão 3.0.0. Detalhes em `docs/F4E-2B2-IDENTIDADE-INERTE-20261103.md`.


### F4E-2B1 — contrato inerte de dispatch (PR #233; PRE-DEPLOY)

Contrato isolado e ainda não integrado ao executor: `CampaignDispatchIdentity` valida somente formato em memória; não comprova vínculo, posse ou imutabilidade persistida. `require_campaign_dispatch_authorization` sempre recusa, independentemente de flags. Não altera fluxo legado, não autoriza campanha e não protege o executor central de produção atual. Sem criação de jobs/posts/reservas, SQL, migrations, configuração ou chamadas externas. Antes de qualquer execução: identidade verificável e protegida entre reserva, ocorrência, job e post; guardas transacionais no claim e imediatamente antes da chamada externa; compatibilidade nos dois ambientes; proteção de mídia e revisão do acesso service_role. CI/revisão/deploy não confirmados neste registro. `VERSION=3.0.0`.


### F4E-2A — fechamento pós-deploy em staging

**F4E-2A STAGING LIVE (03/11/2026, substitui nota histórica PRE-DEPLOY):** [PR #231](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/231) integrada somente em `staging` no squash `8e0c6b44f84d4fedb9951ef589369127ecaab407`; [CI #773 SUCCESS](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41707521280) (API 1.170, scheduler 175 + 1 xfailed, SQL 4, segurança/web 27, build frontend e PostgreSQL 16 isolado). Render `dep-dbl3ov15efls73bmmpd0` LIVE no mesmo SHA. Navegador após deploy: `GET /api/health/ready` = `{"status":"ok"}`; `GET /api/campaigns/drafts/11111111-1111-1111-1111-111111111111/preflight?expected_revision=1` sem sessão = `{"detail":"Não autenticado"}`. Supabase compartilhado: `campaign_reservations_f4e` = 0, `campaign_occurrences_f4e` = 0 após deploy. Preflight permanece exclusivamente leitura e parcial (`reservation_available=false`, `reserved=false`, `activated=false`, `checks_complete=false`), sem jobs, reservas, mídias, redes, migração nova nem postagem. `main` não foi alterada. Próximo gate F4E-2B: proteger caminho central/legado de execução e pré-envio com vínculo imutável fail-closed e flags OFF, mais mídia persistente, cota transacional por rede e conta, `service_role`, OAuth, congelamento T−30 e downgrade. Autorização separada obrigatória para qualquer promoção a `main`, reserva ou teste externo. [Vault PR #43](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/pull/43) documenta os riscos.


### F4E-2A — preflight parcial, PR draft

**F4E-2A PRE-DEPLOY (PR #231):** preflight autenticado de leitura parcial para rascunho e revisão, política de plano, cronograma e volume por rede. Retorna `preflight_only`, `checks_complete=false`, `reservation_available=false`, `reserved=false`, `activated=false`; não reserva, não chama RPC, não gera jobs/posts e não prova OAuth, retenção física de mídia ou vaga concorrente. Antes de qualquer reserva/execução: proteger mídia e rascunho contra exclusão concorrente, rever writes diretos service_role e validar guardas de dispatch em ambos ambientes. CI, revisão e deploy ainda não confirmados neste registro; `VERSION=3.0.0`.


### 03/11/2026 — Fechamento F4E-1 em staging LIVE (após PR draft)

- [PR #229](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/229) mesclada apenas em staging: squash `24c45b671e416d071c80c1c914eecaf6344db0b9`; [CI #764](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41702740725) SUCCESS com PostgreSQL 16; Render `dep-dbl3aibbc2fs738kfllg` LIVE no SHA; `/health` e `/api/health/ready` = `{"status":"ok"}`.
- Supabase compartilhado com migration `20261103191911` e marcador único `public.migrations` para `074_f4e1_inert_campaign_reservations.sql`; tabelas 0/0, RLS/grants restritivos, sem nova execução, posts, jobs ou campanhas reais. Main/produção sem promoção de código.
- Rafa confirmou tags, mensagens, criação e separação de perfis em mobile. Planos/checkout, F4E-2, barreiras de dispatch, redes/OAuth/mídia e downgrade continuam pendentes. `VERSION=3.0.0`. Os registros de PR draft abaixo são históricos pré-merge.

### F4E-1 — DDL inerte aplicada, PR draft

- DDL aplicada ao Supabase compartilhado com autorização de Rafa, registrada no histórico Supabase (`20261103191911`) e em `public.migrations`. Reservas e ocorrências estavam vazias na inspeção; sem executor, jobs F4E, publicações, merge ou deploy de main/produção.
- [CI #755](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41701678290) passou para o SHA anterior; [CI #761](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41702528589) está em andamento no momento deste registro. A CI do novo SHA deve ser consultada separadamente.
- Rafa confirmou tags, mensagens e perfil em mobile; QA visual desktop completo não comprovado. Escolha de plano e F4E-2 permanecem pendentes; VERSION segue `3.0.0`.

### Fechamento verificado F4D em staging — 03/11/2026
- 03/11/2026 — F4D **integrada apenas em staging**: [PR #219](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/219) squash `9adbd5a455022acecc580c7daba75bd445a8ec22`, [CI #728](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41696637695) SUCCESS (API 1.165; frontend 38 contratos + TypeScript/Vite; scheduler 175 + 1 xfailed; SQL 4; segurança/web 27; externo skipped esperado). Render staging `dep-dbl2obp5efls73f9durg` LIVE no mesmo SHA; browser confirmou `/health` e `/api/health/ready` como `{"status":"ok"}`. UI autenticada desktop/mobile ainda não verificada. Nenhuma migration/SQL/ativação/job/post externo, cobrança ou alteração de `main`/produção. `VERSION=3.0.0`.
- F4E auditada somente leitura: dispatch central de produção pode reivindicar agendamentos com origem staging se a configuração de dispatch estiver habilitada (flag real Render não verificada); separar F4E-1 inerte/transacional de F4E-2 execução protegida e não inserir campanha em `schedulers`/`publish_jobs` antes de guardas simultâneos nos dois ambientes. Não houve DDL nem autorização de ativação.


### Added — F4D: plano da conta, consumo e acesso (PR, sem deploy)
- Badges canônicos Free/Pro/Premium/Administrador, resumos de uso/limite por conta/perfil e bloqueios contextuais sem preços, cobrança ou checkout.
- GET autenticado read-only `/profiles/usage` com counts exatos e limites auditados; Agora/cron/ativas sem consumo comprovado permanecem indisponíveis, nunca zero fictício.
- Campanha usa caps do servidor, mantém leitura/exclusão após downgrade; automação visível como vitrine e indisponível mesmo quando habilitada pelo plano. Contratos frontend SSR/helpers/a11y e API incluídos na CI.
- Sem SQL/DDL, ativação, jobs, envio externo, mudanças de scheduler, main ou VERSION=3.0.0. CI/QA/deploy final pendentes nesta nota.

### Status operacional — F4C2 em staging (03/11/2026)
- PR #217 squash-merge em `staging` SHA `d80f60d289c314064fa6ac728c4b23f898a767c2`, CI #722 verde, Render deploy `dep-dbl2d1k9v7es73datmag` LIVE; `/health` e `/api/health/ready` respondem `{"status":"ok"}`. Sem schema novo, envios reais, UI autenticada testada ou promoção de `main`. F4E reserva de campanhas ativas e F4D interface continuam pendentes.


### Added — F4C2: guardas preparatórios de campanhas (PR, sem merge/deploy)
- Política server-side de conta/catálogo auditado, sem cache e com falha fechada; acesso Free bloqueado para prévia/criação/edição/upload, preservando consulta e exclusão após downgrade.
- Pro 15 dias inclusivos/3 publicações diárias, Premium 30/15, contagem de cada rede na rotação por data local dos rascunhos; ADMIN sem teto comercial e com segurança absoluta de 30 dias preservada.
- Endpoint autenticado `/campaigns/limits` informa limites e elegibilidade sem simular execução ou uso: ativação/automação indisponíveis, consumo ativo null. Guarda de automação exclusivamente Premium/ADMIN para futura integração.
- Testes de autoridade de plano, alias Plus, limites, ownership, downgrade e falhas; sem ativação, job ou publicação. Quota de campanhas simultaneamente ativas permanece pendência transacional F4E (rascunhos não consomem vagas), **sem migration 074 ou SQL aplicado**, VERSION=3.0.0 e frontend F4D intocados.


### Added — F4C1: reservas de cota para publicação por perfil (staging LIVE)
- Migração 073 **aplicada ao Supabase compartilhado após autorização expressa e implantada em staging**: reservas transacionais de envio imediato por rede na janela móvel de 60 minutos e horários recorrentes por dia da semana; lê a política da conta na tabela 072 e considera agendamentos legados sem dupla contagem.
- FastAPI reserva antes de criar agenda, trata excesso como bloqueio PT-BR da rede, compensa falha de criação sem liberar envio externo incerto e reaproveita reserva ao despachar um post "Agora". ADMIN ignora cota comercial, mas não ownership/regras de rede.
- Testes mockados de escopo, limites, falha fechada e batch parcial; fixture de Supabase fake ampliada após a CI #713 detectar 15 regressões de contrato. CI [#714](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41600926342) passou (API + frontend); PR #215 integrada somente em staging (`397f0f7`), CI #717 verde, Render `dep-dbl20fss728c739c6kag` LIVE; `/health` e `/api/health/ready` OK. Banco 073 verificado com RLS/RPCs restritas e registro único em `public.migrations`. Nenhum post externo ou promoção para `main`; Vault PR #38 integrada. `VERSION=3.0.0`. `VERSION=3.0.0`.

### Changed — F4B2: perfis conforme plano e isolamento reafirmado (staging)
- Limites de perfis por conta: Free 1 total, Pro 3, Premium 5; ADMIN sem teto comercial. Nova RPC transacional valida plano/contagem no banco; `/profiles` de staging a utiliza e a versão antiga de produção continua com trigger de teto 3, por compartilharem Supabase.
- Catálogo, Shopee e chave Gemini/IA seguem compartilhados na conta; listas (decisão confirmada), credenciais sociais, posts, agendas e histórico continuam segregados por perfil. Documentação e testes atualizados sem alterações em publicações reais.

### Added — F4B: catálogo persistente de quotas e consumo atômico (staging)
- Matriz Free/Pro/Premium confirmada; Pro suporta **2** campanhas ativas por perfil, Premium **5**, e postagem em cada rede conta individualmente.
- Migração aditiva 072 introduz plano canônico por conta, tabela auditável de limites e RPCs atômicas de criação de produtos/listas, sem trigger comercial global no Supabase compartilhado.
- API staging aplica 100/500/2.000 produtos por conta e 20/20/100 listas por perfil com isenção comercial de ADMIN. Postagens imediatas/recorrentes, ativação de campanhas e criação de perfis feita na F4B2; demais controles seguem para F4C; nenhuma publicação real é disparada por esta alteração.

### Changed — F4A: identificação visual de planos (staging)
- Matriz Free/Pro/Premium, exceção ADMIN e fases de cotas registradas em `docs/PLANOS-F4-POLITICAS-E-FASES-20261103.md`, sem prometer restrições ainda não aplicadas ao backend.
- Cards de perfis passam a tratar `plus` legado como rótulo `Pro`, aceitam `pro` futuro e exibem `Administrador` se papel de ADMIN já estiver confirmado pela sessão. Migração, faturamento e regras de postagem continuam intocados neste incremento.
- Conta de teste `RafaelTesteCliente` recebeu etiqueta `premium` no perfil principal via operação controlada no Supabase, confirmada por releitura; conta ADMIN não sofreu alteração de banco.


### Added — F3C: postagens por dia e exclusão de rascunhos (PR #211, integrada em staging)
- Campanha por lista agora usa seletor de **1 a 15 postagens por dia**, com horários uniformemente distribuídos entre início e fim dos dias selecionados. Uma postagem usa o início da janela; janela pequena para múltiplas postagens é rejeitada.
- Rascunhos históricos com `interval_minutes` são convertidos ao carregar para `posts_per_day` (respeitando teto de 15 e exigindo revisão da prévia); nenhuma migração SQL necessária, pois o campo `schedule` é JSONB.
- Botão **Excluir** na lista de rascunhos, com confirmação inline na página; endpoint próprio protegido por usuário, perfil e revisão. Arquivos privados de campanha são removidos **antes** da exclusão da linha; falhas bloqueiam a operação, sem tocar em produtos, posts ou jobs.
- CI [#41581370451](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41581370451) verde, merge `140ea06`, Render `dep-dbkmmf7lk1mc73e1o2p0` LIVE e `/health` OK. Testes focados em planejamento, limites e exclusão segura; `main` e produção preservados. **Não habilita disparo/ativação nem altera planos por plataforma.**


### Added — F3B: nome da campanha e mídias persistentes por produto (PR #209, staging)
- Cada campanha recebe um nome próprio de até 120 caracteres, independentemente da lista usada; nomes distintos aparecem na recuperação de rascunhos.
- Preparação por produto permite anexar imagens/vídeos de PC/celular ao rascunho salvo, com até 10 arquivos de 50 MB, seleção da imagem principal Shopee preservada. Referências em tabela independente dos temporários que expiram em 24h.
- Bucket `post-media` permanece privado, com prefixo específico, sanitização de mídia existente, escopo usuário/perfil/produto, RLS/trigger e opção de excluir anexos. Migração `campaign_names_media_071` **aplicada com autorização** ao Supabase compartilhado em 03/11/2026, com RLS, grants e ownership verificados; PR #209 mesclada por squash somente em `staging` (`5ec24df`). Nenhuma ativação, post/job ou disparo.
- Layout do editor permanece integrado à página e responsivo. Regras técnicas em `docs/CAMPANHA-F3B-NOME-E-MIDIAS-20261103.md`.

- CI [#41578367282](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41578367282) aprovada; Render staging `dep-dbkm74ks728c738ritc0` LIVE, migration 071 reexecutada sem erro no boot, `/health` OK; nome e controles de anexos conferidos na UI autenticada. Nenhum arquivo de teste persistente nem publicação criada. `main` e versão `3.0.0` permanecem intocados.

### Fixed — F3A: reinício seguro após aplicação da 070
- PRs [#207](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/207) e [#208](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/208) mescladas em `staging`. O migrador reexecutava a 070 no boot e falhava no trigger já existente após a aplicação manual; guarda idempotente corrigiu e o deploy terminou LIVE com `/health` OK. Incidente documentado no Vault #61; `main` inalterada.


### Added — F3A: rascunhos de campanha persistidos (PR #207, mesclada staging)
- Nova API de rascunhos `/campaigns/drafts` para salvar, listar, consultar e revisar com controle por usuário/perfil e revisão otimista; preserva snapshots separados de título, texto, link, redes e foto Shopee por item.
- Página `Criar POST` com ações para salvar e recuperar rascunhos do servidor, mantendo a cópia local como proteção. A operação não cria posts, jobs, reservas de agenda ou publicações.
- Migration `070_campaign_drafts.sql` aditiva com RLS, integridade de dono/perfil/lista e índice; **aplicada com autorização de Rafa em 03/11/2026** ao Supabase compartilhado sob o nome `campaign_drafts_070`; inspeção confirmou RLS ativo, zero policies para acesso direto, `anon`/`authenticated` sem SELECT, `service_role` com SELECT/INSERT e trigger de ownership. Integração validada em staging após correção de inicialização na PR #208.
- Mídias próprias de campanha (fotos/vídeos enviados pelo usuário) exigem persistência durável separada antes da ativação. A publicação única mantém suas fontes e uploads existentes; não houve alteração nela.


### Added — preparação por produto da campanha (staging, sem ativação)
- Campanha por lista tem editor em página, por produto, para título, texto principal, texto específico por rede, link de afiliado, redes com credenciais válidas e opção de foto principal Shopee.
- Snapshots locais independentes por usuário/perfil/lista, sem modificar a lista-fonte; restauração preserva campos apagados, ordem e IDs permitidos. Prévia permanece somente leitura, sem gerar posts/jobs ou publicar.
- Contratos executáveis dos snapshots integrados ao gate frontend. Upload persistente de fotos/vídeos por item, IA em lote, persistência transacional e ativação serão entregas posteriores; publicação única e seus uploads estão intactos.

### Fixed — ícones de navegação e prévia (staging)
- Corrigido o menu **Criar POST**: o ícone Lucide `square-pen` já era solicitado pelo SideRail, mas não constava do registro central de `Icon`, resultando em espaço vazio. Corrigido também `calendar-search` no botão de prévia da campanha.
- Contrato automático de ícones da navegação e ação de prévia impede novas referências silenciosamente sem renderização. Sem alteração de rotas, permissões, dados ou publicação.

### Added — campanha por lista: prévia segura (PR #204, staging)
- Novo modo **Campanha por lista** na página `/posts/criar`, mantendo **Publicação única** e suas mídias/agenda anteriores sem regressão.
- Seleção de lista do perfil, ordenação local, até 30 dias inclusivos, dias/horários/intervalo, revezamento de um produto por horário e prévia de cobertura no fuso de Brasília.
- `POST /campaigns/preview` autenticado e somente leitura, com escopo de lista/produto e resposta sem ativação; rascunho local segregado. Não cria posts, jobs ou publicações. Registro: `docs/CAMPANHA-POR-LISTA-PREVIA-20261103.md`.

> **SemVer:** `VERSION=3.0.0` permanece a última versão publicada. Funcionalidades novas compatíveis de `[Não lançado]` são candidatas a **3.1.0** na próxima promoção **expressamente aprovada** de staging para main. Este registro não é uma release; não antecipar bump nem integrar `main` sem revisar o lote e obter aceite.


### Changed — página Criar POST sem aparência de modal (staging) e decisão R06
- Formulário de `/posts/criar` integrado ao layout do site: sem cartão central, com regiões de produto/mídia e texto/agendamento, duas colunas em desktop e fluxo fluido em tablet/celular. Prévia da criação passa a ser conteúdo da página, sem overlay em telas pequenas.
- Experimento de galeria extra Shopee **encerrado como indisponível na integração atual**: 3 sondagens autenticadas `productOfferV2` rejeitaram `imageUrls` e o link original real consultado exigiu login de comprador. Preservados imagem principal da Shopee e uploads locais de foto/vídeo.
- Sem alteração de APIs, worker, cron, tabelas, credenciais, publicação externa ou produção. Registro técnico: `docs/CRIAR-POST-LAYOUT-GALERIA-SHOPEE-20261103.md`.

### Added — Criar POST em página dedicada (staging, R01/R02 parcial)
- Menu lateral `Criar POST` e rota privada `/posts/criar`, transferindo compositor do modal para página responsiva; histórico permanece em `/posts`.
- Preservados criação imediata/recorrente, produto individual, foto principal Shopee, upload local de fotos/vídeos, IA, rascunhos, preview, validações e fluxo de dispatch/erros existente.
- Nenhuma API, agendamento, banco ou publicação externa modificada. Galeria adicional Shopee e edição de mídia futura permanecem pendentes de fonte oficial/versão segura.

### Added — edição futura de texto em staging (F1 isolada, sem enviar post)
- Revisões imutáveis de texto para ocorrências ainda não reivindicadas a mais de 30 minutos, preservando ID do post, agenda, foto Shopee, fotos/vídeos enviados e histórico. Seleção atômica de snapshot pela hora original no claim com suporte a retry seguro; endpoint de leitura separado do detalhe existente.
- Editor de texto sob demanda nos detalhes de posts agendados; rede, produto, mídia e horários não são alterados. RLS e banco seguem a migração 069 já aplicada e registrada; nenhuma publicação externa de teste.


### Added — teste isolado da galeria Shopee (somente staging; sem postagem)
- Endpoint autenticado e de leitura `GET /api/products/{id}/shopee-gallery-probe`, com `productOfferV2(itemId)`, teste condicional do campo `imageUrls`, fallback para `imageUrl`, filtragem de CDNs Shopee e escopo por conta. Usa apenas credenciais Shopee já cadastradas no backend; não modifica credenciais, agendamentos, uploads ou posts. Disponibilidade real de fotos adicionais depende de consulta autenticada em staging, sem assumir campo suportado.
- Testes mockados de erro de schema, rate limit, foto única, múltiplas fotos, segurança de URL e autenticação. Sem migração SQL e sem alteração de UI nesta PR.

### Added — piloto F0 no staging (gate desligado)
- Preparação aditiva da migração 068 e de escopos idempotentes para despacho central de agendas novas; antigas agendas de staging permanecem `legacy`. Reconciliador central só funciona com `ORBITAL_CENTRAL_DISPATCH_ENABLED=true` **em etapa futura**. Nesta implantação: flag desligada, nenhum job transferido, nenhum post de teste, sem mudança em main.
- Testes de criação/claim/rollback/espelhamento/cancelamento/`Agora` e expiração; detalhamento em [F0 — piloto no staging](docs/F0-CENTRAL-DISPATCH-STAGING-PILOT-20261102.md).


> Toda alteração integrada em `staging` deve ser registrada aqui por PR. `VERSION` é a fonte oficial da versão; nenhuma mudança passa para `main` sem classificação SemVer, changelog e validação. A próxima versão só é decidida na promoção aprovada.

## [3.0.0] - 2026-11-02

### Breaking Changes
- Novas publicações aceitam **um único produto**; composições com múltiplos produtos são rejeitadas no frontend e pela API. Registros anteriores são preservados.
- Foi removida a opção de **criar agendamento avulso ("Agendar")**. Novos posts utilizam `Agora` ou `Recorrente`; agendamentos históricos e o disparo interno de `Agora` não são apagados.

### Added
- Persistência local e isolada por conta/perfil de rascunhos de formulários, com recuperação após atualização ou fechamento e respeito a campos apagados intencionalmente; arquivos e segredos não são salvos.
- Geração de descrição por IA **individual por rede social**, com variantes editáveis, revisão dos limites de texto e hashtags e mensagens de compatibilidade de mídia.
- Identificador público `#ID` único e crescente para cada post, preservado em edições e não reutilizado após exclusão.
- Detalhamento de ocorrências recorrentes por dia/horário, status discreto e última publicação efetivamente confirmada.
- Entrada pública da landing e fluxos de autenticação Supabase Auth/Google, preservando o acesso legado controlado da conta de revisão Shopee.

### Changed
- Seletor de horários do desktop com controles de 24 horas e atalhos; experiência nativa Android mantida.
- Campo de upload de imagem/vídeo reposicionado imediatamente abaixo de "Usar fotos dos produtos Shopee".
- Mensagens de falha objetivas para USER; diagnóstico de API detalhado e recolhível restrito a ADMIN.
- Navegação, prévia e consulta dos posts reorganizadas sem permitir alteração de publicação já programada/tentada.

### Fixed
- Isolamento de identidade de usuário/perfil/post/agenda/ocorrência, inclusive para múltiplas publicações no mesmo segundo.
- Agrupamento de posts exclusivamente por `group_id` explícito, eliminando união indevida por texto ou horário.
- Preflight de indisponibilidade do scheduler antes de gravar post/mídia e preservação do rascunho na falha; separação de jobstores e fila por ambiente no código atual.
- Tratamento de retorno de postagem incerta, evitando apresentar envio não confirmado como sucesso ou repetir automaticamente uma publicação.

### Security
- Preservadas validações de dono/perfil, separação USER/ADMIN, sanitização das falhas da Meta e proteção de segredos e tokens.
- A conta `RafaelTesteCliente` continua reservada para a revisão Shopee, sem alteração de senha ou credenciais nesta atualização de versão.

### Verification and known limitations
- Código de funcionalidade já integrado à `main` pelos PRs #190/#192; documentação e configuração operacional devem ser verificadas por SHA/CI/Render, não inferidas a partir da versão.
- **Não houve novo teste de publicação real em redes sociais nesta atualização de metadados**; erro HTTP 403 Threads e permissões externas permanecem sob acompanhamento.
- O Supabase é compartilhado por `staging` e `main`. A implementação atual possui agendadores separados por ambiente; a decisão posterior de Rafa de **centralizar o despacho em produção** ainda exige adequação técnica independente, não incluída neste release documental.
- Referências: PRs #181, #184, #185, #186, #187, #189, #190, #191, #192 e #195.

## [2.7.0] - 2026-10-21

### Added
- Posts recorrentes podem ter ate cinco horarios por dia selecionado.
- Upload de MP4 e reencodificado antes de ser salvo no Storage, com limites de duracao, resolucao, tamanho, tempo e concorrencia.

### Fixed
- "Postar agora" e publicado imediatamente sem etiqueta de agendamento; "Agendar" conserva a data e a etiqueta apropriadas.
- Seletor de data/hora e estado do historico de posts alinhados ao tipo de publicacao.

### Security
- Video segue disponivel, mas o FFmpeg roda no container da API e nao ha scanner antivirus isolado. Nao declarar arquivos livres de malware; ver `docs/POST-MEDIA-SECURITY.md`.

### Verification
- Suite da API: 852 testes passaram com as versoes de dependencias fixadas no projeto. Deploy de `staging` do commit `ffbd470` confirmado live; upload autenticado de video no Render nao foi comprovado.

## Arquivo histórico — integração de multi-perfil (estado documentado em 2026-10-06)

> Registro histórico preservado; esta seção descreve a situação de sua época e não indica pendência atual da `main`.
>
> Branch `chore/phase-12-integration`. A versão (`VERSION`) só sobe no merge para `main`.
> Migrações exigidas: 037, 038, 039, 040, 041 e 042 (aplicar no Supabase antes do deploy, ver `docs/RULES.md` item 11).

### Added
- Multi-perfil completo: `profile_id` nas 14 tabelas restantes que tinham `user_id`
  (migração 038: credenciais das 7 redes, `credential_checks`, `posts`, `medias`, `schedulers`,
  `activities`, `request_logs`, `audit_events`), com `ON DELETE SET NULL`, índice e backfill para o
  perfil principal.
- Posts, mídias, credenciais das redes (leitura, escrita, OAuth, teste de conexão), dashboard,
  notificações, catálogo, logs/auditoria e backup/restore passam a respeitar o perfil ativo;
  scheduler e bots usam a credencial e as atividades do perfil do post (com fallback por `user_id`).
- Migração 037: trigger que impõe o limite de 3 perfis por conta no banco (atômico).
- UI de perfis: editar e excluir perfil, perfil ativo na TopBar, ativação sem recarregar a página;
  backup/restore sem `alert`/`confirm`.
- `GET /auth/me` devolve o `profile_id` ativo; o frontend lê o perfil ativo dali (sem `localStorage`).
- CI: job `frontend` (`npm ci` + `npm run build`), `.github/dependabot.yml` e
  `.github/pull_request_template.md`.
- `Dockerfile`: `HEALTHCHECK` em `/health`.
- `SECURITY.md` com contato e política de reporte.

### Changed
- Migração 039: removido o UNIQUE de `shopee_credentials.app_id` (mesma API Key em mais de um
  perfil) e o de `credential_checks` virou `(user_id, profile_id, network)`.
- Migração 040: índice único de `credential_checks` usa coalesce(profile_id, uuid('00000000-0000-0000-0000-000000000000'))
  para deduplicar NULLs em casos de fallback por `user_id`.
- Migração 041: `products` deixa de ser único por `(product_id, user_id)` e passa a `(user_id, product_id, coalesce(profile_id))`;
  o mesmo produto pode existir em 2 perfis. Restore cria/atualiza o produto do perfil ativo e `POST /products`
  duplicado no mesmo perfil devolve 409.
- CI: flake8 bloqueante para erros graves, Python 3.13, cache de pip/npm e `concurrency`.
- CD: dispara via `workflow_run` somente após CI verde em `main`; `curl -f`; `concurrency`.
- `gunicorn.conf.py`: `timeout = 120` e supervisão do subprocesso uvicorn (reinício com backoff).
- `Dockerfile` roda como usuário não-root.
- `.env-example` lista as variáveis realmente lidas pelo código e corrige X/TikTok (app único da
  plataforma, não por usuário). Documentação (`README`, `docs/`) atualizada.

### Fixed
- Troca de senha invalida JWTs antigos (claim `pwv`); tokens sem o claim continuam aceitos.
  Ativação de perfil (`POST /profiles/{id}/activate`) recalcula `pwv` no novo JWT.
- `profile_id` do token é validado contra o dono; se inválido, cai no perfil principal.
  Token sem claim `profile_id` defaults ao perfil principal, inclusive em `GET /auth/me`.
- `product_ids` de posts são validados por dono/perfil (400 Bad Request se inválido).
- Registro provisiona o perfil principal com rollback do usuário órfão em caso de falha; admin que
  cria usuário também cria o perfil principal.
- Rate limit em criar perfil, backup e restore.
- Supervisor uvicorn em `gunicorn.conf.py` (reinício com backoff em caso de crash) sem deixar processo órfão.
- `generate-copy` não devolve a exceção ao cliente; log de debug de páginas do Facebook removido.

### Notes (limitações conhecidas / pendências manuais — atualizado 2026-10-06)
- Pendências manuais de Rafa (não são código):
  - [CONCLUÍDO, 2026-10-05] Env vars do serviço `shopee-bot-staging` no Render.
  - [CONCLUÍDO, 2026-10-05] Trocar o branch de produção no Render de `master` para `main`.
  - [CONCLUÍDO, 2026-10-05] Secret `RENDER_STAGING_DEPLOY_HOOK_URL`.
  - [CONCLUÍDO, 2026-10-05] Callback URLs das redes (X, Meta, TikTok) nos painéis de desenvolvedor.
  - [CONCLUÍDO, 2026-10-05] Conectar X, Instagram e TikTok; recolar o Client Secret do TikTok.
  - [POSSÍVEL, NÃO ATIVADA] Branch protection (GitHub Pro ativo desde 2026-10-05, mas ainda não configurada).
  - [CONCLUÍDO, 2026-10-06] Aplicar as migrações 037/038/039/040/041/042 no Supabase — verificado via MCP: 6 migrações registradas em `public.migrations` (linhas); nenhum `profile_id` NULL em `posts`/`shopee_credentials` após backfill. Staging e produção compartilham MESMO banco. **Risco conhecido**: Código de produção antigo (sem este PR) usa upsert `on_conflict (product_id, user_id)` no restore; após migração 041 (que muda para `(user_id, product_id, coalesce(profile_id))`), o restore falhará com violação de constraint. Solução: Merge desta branch (PR #10) corrige o restore. Prevenção: Aplicar migrações antes do deploy do PR #10. Ver `docs/RULES.md` item 11 para detalhe.
  - Merge dos PRs da branch `chore/phase-12-integration` em `main`.
  - Teste real de upload no container não-root (verificação de disco/permissão).
- Correção de nota anterior (2026-10-05): a limitação "`profile_id` ainda NÃO cobre credenciais,
  posts…" da 2.0.0 deixa de valer nesta branch.

## [2.0.0] - 2026-09-30

### Added
- Sistema de perfis por conta, limitado a 3 (1 principal + 2 secundários): tabela
  `profiles` (migração 035, com backfill do perfil principal) e `profile_id` aditivo
  apenas em `products` e `product_lists` (migração 036).
- CRUD de perfis e ativação de perfil (`api/routers/profiles.py`); ativar reemite o JWT
  com o claim `profile_id`.
- Produtos e listas escopados pelo perfil ativo, compatível com token antigo (sem claim);
  endpoints por ID isolados entre perfis da mesma conta.
- Upload de avatar de perfil no Supabase Storage (bucket `avatars`), limite de 5MB e
  validação por magic-byte.
- Página "Perfis" (`/profiles`) com grid de cards (criar, ativar, enviar avatar).
- Página de Configurações (`/settings`) com troca de senha (`PUT /settings/password`,
  com rate limit).
- Branch `staging` criada e serviço `shopee-bot-staging` criado no Render (plano Free), MAS ainda sem env vars/deploy hook configurados — ver `docs/TASK.md` item 10.13 (pendências manuais).
- Fluxo Git Flow (`main`/`staging`/`feature/*`, SemVer só sobe no merge pra `main`; proteção automática de branch indisponível no plano Free do GitHub — ver `docs/TASK.md` 10.13).

### Changed
- Página "Usuários" renomeada para "Perfis" (rota `/profiles`); a seção admin de contas
  de login foi preservada na mesma página.
- Branch padrão do repositório renomeada de `master` para `main`; referências da CI
  atualizadas.

### Notes (limitações conhecidas)
- `profile_id` ainda NÃO cobre credenciais de redes, posts, mídias, activities,
  schedulers, audit_events e request_logs: continuam escopados só por `user_id`.
  Previsto para uma rodada futura.
- Avatar via OAuth Google/Apple está fora de escopo (o login do projeto é usuário/senha).
- Free/Plus/Premium é apenas rótulo; não há cobrança.
- Proteção automática de branch não está ativa (limitação do GitHub Free em repositório
  privado); o fluxo Git Flow depende de disciplina. Ver `docs/RULES.md` item 1.
