# Entrada pública e navegação da landing Auto Orbital — design aprovado (01/11/2026)

## Intento e decisão de Rafa
Com o protótipo desktop/mobile aprovado, o site deve abrir a apresentação para quem chega sem sessão e levar quem já possui sessão autenticada diretamente ao painel. Endereços técnicos permanecem em inglês. Links destinados à divulgação devem sempre permitir ver a apresentação mesmo que o receptor esteja logado.

## Abordagens avaliadas
- **Escolhida: `/` como entrada inteligente + `/presentation` pública estável + `/app` como dashboard.** Atende entrada espontânea, sessão válida e compartilhamento previsível sem mudar a pilha.
- `/` sempre pública e CTA entrar: mais simples, mas descumpre redirecionamento automático para quem já está logado.
- `/` sempre privada, landing apenas em subrota: preserva o comportamento antigo, mas descumpre o pedido de página inicial.

## Contrato de URLs
| URL | Sem sessão | Sessão USER | Sessão ADMIN |
| --- | --- | --- | --- |
| `/` | Renderiza landing aprovada | Redireciona a `/app` | Redireciona a `/admin/overview`, exceto preferência explícita de visitar site, quando `/app` |
| `/presentation` | Landing | Landing | Landing |
| `/apresentacao` | Redireciona a `/presentation` | Redireciona a `/presentation` | Redireciona a `/presentation` |
| `/app` | Encaminha a `/login` | Dashboard do cliente | Dashboard do site (ou admin se navegação explícita) |
| `/login` | Login existente | Sem alteração neste escopo | Sem alteração neste escopo |
| `/admin/...` | Protegido | 403/redirect conforme contrato existente | Protegido por papel ADMIN |

Os caminhos `/products`, `/lists`, `/posts`, `/credentials`, `/profiles`, `/settings`, `/admin/...` e os endpoints OAuth atuais permanecem funcionais; renomeação total de rotas e APIs fica fora do escopo. Não remover a rota pública `/apresentacao` sem alias de compatibilidade. Rota da página sempre em inglês: `/presentation`.

## Autenticação e segurança
- A decisão de `/` deve chamar `GET /api/auth/me` (cookie httpOnly validado pelo backend), não aceitar a mera indicação `isAuthenticated` persistida no localStorage.
- Falha 401 significa visitante para a landing; falha de rede/5xx não autoriza expor o painel nem destruir credenciais locais. Exibir a landing pública ou estado seguro sem loop.
- A página `/presentation` deve funcionar sem verificar sessão e sem expor dados do usuário.
- Login por email/Google e exceção temporária de suporte `RafaelTesteCliente` permanecem. O callback Google atualmente retorna `/`; a nova decisão da raiz deve encaminhar conforme papel após verificar cookie.
- Preservar `isAdminVisitingSite` e a transição intencional ADMIN → site sem provocar loop.

## Compartilhamento e SEO
- O link de divulgação recomendado será `/presentation`, sempre público. Abrir `/` na sessão autenticada encaminha ao painel por decisão do dono — compartilhar somente `/` não garante visualização da landing para destinatários autenticados.
- A resposta HTML inicial precisa conter `og:title`, `og:description`, `og:image`, Twitter Card, `description`, imagem pública absoluta HTTPS e título da marca; social bots podem não executar JavaScript. **Não usar `og:url` ou canonical fixos de produção no HTML compartilhado por staging e produção**: manter a URL realmente divulgada até existir metadata dinâmica por host. Validar com prévia social real antes da comercialização.
- Não trocar automaticamente domínio, configuração de Auth do Supabase, DNS ou SMTP; domínio próprio será etapa posterior. Manter staging não indexável inclusive para crawlers sem JS (`X-Robots-Tag` no HTML do host staging) e evitar promessa de lançamento comercial.

## Não objetivos
- Não criar vídeo/Scroll World definitivo, planos/preços, novos provedores, banco, migration, pagamento ou serviço pago.
- Não promover a `main`/produção nesta fase; somente branch de trabalho → PR para `staging` → CI e homologação.
- Não modificar textos persuasivos, cenas ou design system do protótipo aprovado sem pedido editorial posterior.

## Aceite técnico
1. Anônimo na raiz vê a landing e botões existentes.
2. USER com cookie válido em `/` vai para `/app`; ADMIN vai a `/admin/overview`, salvo visita explícita ao site.
3. `/presentation` sempre abre a landing, com ou sem sessão, e antiga `/apresentacao` redireciona.
4. `/app` mantém dashboard protegido e navegação/links internos seguem operacionais.
5. Login Google/e-mail/suporte mantém fluxo e caminhos sem loop.
6. Resposta HTML estática inclui metadados coerentes e imagem de compartilhamento HTTPS; verificação real com bots é separada.
7. Frontend TypeScript/Vite, testes pertinentes e smoke de staging passaram antes de qualquer pedido de promoção a main.

**Autorizações:** Rafa aprovou a topologia na conversa anterior e autorizou iniciar a fase em 01/11/2026. Produção continua bloqueada até nova ordem.