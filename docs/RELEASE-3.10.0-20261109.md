# Auto Orbital 3.10.0 — Release MINOR (rascunho: promoção em andamento, ainda não confirmada em produção)

**Data:** 09/11/2026 (BRT)
**Autorização:** Rafa autorizou expressamente o merge na `main` depois do merge na `staging` ("faça o merge na main completo de tudo que for necessário para o funcionamento da produção").
**Repositório:** raffastudioproducoes-cloud/shopee_bot-main
**Versão:** 3.9.0 → 3.10.0 (**MINOR**: o S-02 muda uma regra visível do formulário de produto)
**PR de promoção:** [#403](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/403) (merge commit)

## 1. Escopo publicado

| PR | Conteúdo |
|---|---|
| #397 | Registro da release 3.9.0 |
| #398 | `npm audit fix`: `vite` 6.4.3 → 6.4.6 e `seroval` 1.6.7 → 1.8.0; 2 vulnerabilidades altas → 0 |
| #399 | Chave JWT de teste (41 → 70 bytes), `CampaignDraftItem.copy` com alias (contrato `copy` intacto) e `on_event` → `lifespan` |
| #400 | Bundle inicial 785,8 → 576,1 kB (237,9 → 175,6 kB gzip) com carregamento sob demanda |
| #401 | S-06 (sem token no `localStorage`), S-02 (links/imagens de produto só da Shopee, inclusive no restore), S-03 (dados do produto separados das instruções da IA e links extras recusados), S-01 parcial (helpers de thread exigem o dono; catraca das 52 rotas com ID) |
| #402 | Fase 6: CD verifica o deploy em vez de depender de hook; S-04: limitador único (Redis atômico ou memória com trava); `shope.ee` retirado da lista de links aceitos; bump 3.10.0 |

Sem migration, cron, `pg_net`, gateway ou segredo novos.

## 2. Mudanças visíveis para o usuário

- O formulário manual de produto recusa links e imagens fora da Shopee (`shopee.com.br`, `www.shopee.com.br`, `s.shopee.com.br`; imagens só em CDN Shopee).
- Restore de backup com produto de link externo retorna 422 com o nome do campo.
- O navegador não guarda mais token de acesso; sessões antigas no `localStorage` são limpas.
- Páginas de Ajuda, Configurações, Credenciais, Criar Post e as legais carregam sob demanda (skeleton no primeiro acesso).

## 3. Decisões e incertezas registradas

- **`shope.ee`/`shp.ee` não são aceitos:** a titularidade não foi confirmada em fonte oficial e a Central de Ajuda do Afiliado os cita junto de encurtadores de terceiros. Reativar só após confirmar (gerar um link no painel de afiliados e conferir o domínio).
- **Supabase segue compartilhado** entre staging e produção e as campanhas ativas permanecem ativas (decisão de Rafa).
- **S-04:** a produção continua sem Key Value (só a staging); sem ele o limite é em memória, correto apenas com uma instância. Configurar exige autorização por custo.
- Pendentes: matriz A/B por rota do S-01, S-05 (senha vazada) e teto diário por conta para operações caras.

## 4. Portões e evidências

_(preencher após o deploy de produção)_
