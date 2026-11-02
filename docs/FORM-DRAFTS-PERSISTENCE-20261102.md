# Persistência de rascunhos dos formulários — staging (02/11/2026)

## Objetivo e contrato de UX

Enquanto uma pessoa edita um formulário do Auto Orbital, suas alterações não confirmadas são salvas **localmente no navegador**, incluindo valores vazios deliberadamente digitados/apagados. Reabrir um modal, recarregar a página, perder a internet ou reabrir o navegador deve recuperar o último rascunho quando a mesma conta/perfil e o mesmo formulário forem utilizados. O fechamento/cancelamento **não** apaga o rascunho; um salvamento confirmado pelo backend **apaga apenas** o rascunho correspondente. Uma falha de envio preserva o conteúdo para tentar novamente.

Este mecanismo não é sincronização entre dispositivos, não é recuperação garantida se o usuário limpar os dados do site, navegar em modo privado com descarte de armazenamento, atingir a quota do navegador ou usar um dispositivo diferente. O backend/Supabase **não** armazenam conteúdo não enviado.

## Implementação

- `frontend/src/lib/formDraftStorage.ts`: chaves `auto-orbital:form-draft:v1:<conta>:<perfil|account>:<tipo/ID>`; envelope versionado, carimbo de data, expiração de 90 dias, teto de 256 KiB por rascunho e tratamento de `localStorage` inacessível/corrompido.
- `frontend/src/hooks/useAutosavedDraft.ts`: hidratação por chave, salvamento incremental quando o estado muda, gravação de segurança em `pagehide`; o estado anterior não deve sobrescrever o da nova chave antes de a restauração terminar.
- A chave exige usuário autenticado; para conteúdo vinculado a um perfil (posts, listas, análises e busca em posts), exige também ID do perfil.
- Criar e editar usam chaves separadas; no modo edição, cada registro tem sua própria chave.

## Cobertura funcional

| Área | Persistido | Não persistido |
|---|---|---|
| Posts — novo post | partes de texto, versões por rede, persona, redes, produto único, aba/lista, dias, horas, agora/recorrente, usar fotos Shopee, prévia | arquivos `File` do computador, resultados de publicação, execução de IA, estados transitórios da API |
| Posts — busca | texto de busca por conta/perfil | respostas da API |
| Produtos — criar/editar | todos os campos manuais de cadastro e pré-preenchimento de catálogo | mutações de servidor |
| Produtos — filtros | aba ativa e busca | dados retornados |
| Catálogo Shopee | palavra digitada, busca executada, ordenação, categoria, página | resultados da Shopee e arquivo local |
| Listas — criar/editar | nome, IDs dos produtos selecionados, filtro de seleção | produtos retornados pela API |
| Credenciais Shopee/IA | só App ID público, provedor e modelo (preferências) | **secret, API key, tokens, OAuth**, sempre redigitar |
| Perfis — criar/editar | nome, email, telefone, endereço | credenciais e foto/arquivo |
| Usuários — criar/editar | nome de usuário e nível de acesso | **senha inicial** (sempre deve ser redigitada) |
| Usuários — filtros | busca e acesso | dados administrativos |
| Análises, logs e painel admin | filtros/período/compare | métricas e logs carregados |

Exclusões propositais: login, redefinição de senha, **segredos** de credenciais Shopee/IA, tokens, consentimentos expressos e arquivos do computador. Evita salvar segredos e consentimentos sensíveis no `localStorage`. Uploads locais devem ser selecionados novamente após reload; no formulário de post há aviso explícito quando havia arquivos no rascunho.

## Casos críticos e validação

1. Digitar “A”, fechar sem salvar, reabrir: “A” reaparece.
2. Apagar “A” de propósito, fechar/recarregar, reabrir: **permanece vazio**.
3. Alterar seleção de dia/hora/rede/produto e dar refresh: estado reaparece para a mesma conta/perfil.
4. Iniciar outro perfil/conta: não mostrar rascunho alheio; voltar ao anterior: recuperar o seu.
5. Criar/editar com sucesso: limpar só a chave do formulário salvo. Erro da API: preservar.
6. Arquivos locais: não persisti-los e avisar que precisam ser reselecionados.
7. Senha, API key, OAuth e consentimentos: nenhum conteúdo desses campos no `localStorage`.
8. Armazenamento bloqueado/cheio ou rascunho antigo/corrompido: site continua funcionando, sem exceção fatal.
9. Android, desktop, conta USER e ADMIN: cenários manuais de ponta a ponta ainda dependem da sessão autenticada do proprietário; automação cobre a função de armazenamento e os contratos.

Comandos: `cd frontend && npm ci && node --test tests/form-drafts.test.mjs && npm run build`; CI também executa as suites anteriores. Testes **não** criam posts reais e não alteram o Supabase.

## Escopo e rollout

Primeira entrega somente na branch `staging`, via PR/CI, mantendo `main` e produção intactos. Sem migration ou endpoint novo. Revisão externa de UX em sessões autenticadas permanece obrigatória antes de promover.

## Observações de privacidade

Dados pessoais digitados (por exemplo, nome, endereço e conteúdo de post) podem permanecer neste **mesmo dispositivo** até o salvamento, expiração, limpeza de dados ou exclusão manual do rascunho. Em computadores compartilhados, encerrar a sessão **não apaga** automaticamente rascunhos, pois isso impediria a recuperação após fechar o navegador. As chaves por conta evitam exibir a edição de outra conta na UI, mas o `localStorage` não é um cofre de segurança contra alguém que controle o mesmo navegador. Se a política de segurança exigir criptografia ou logout com limpeza, redesenhar o fluxo com decisão explícita de produto.
