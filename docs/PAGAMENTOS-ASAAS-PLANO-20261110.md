# Pagamentos com Asaas — planejamento (10/11/2026)

**Status:** planejamento aprovado em conversa com Rafa; **nada implementado**.
Fluxo obrigatório: staging com sandbox do Asaas → homologação de Rafa → main com
chave de produção, só com autorização dele.

## 1. Decisões de Rafa (10/11/2026)

- Conta Asaas de produção já aberta e validada (documentos aprovados).
- Planos pagos: **Pro** e **Premium**, com os mesmos períodos e descontos.
- Períodos e descontos sobre o preço mensal:

| Período | Ciclo Asaas | Desconto | Valor cobrado por ciclo |
|---|---|---|---|
| Mensal | `MONTHLY` | 0% | mensal |
| 3 meses | `QUARTERLY` | 2,5% | 3 × mensal × 0,975 |
| 6 meses | `SEMIANNUALLY` | 5% | 6 × mensal × 0,95 |
| 1 ano | `YEARLY` | 15% | 12 × mensal × 0,85 |

- **Preço mensal de referência** (informado por Rafa em 09/11/2026, já exibido na
  apresentação em `frontend/src/pages/presentation/content.ts`): **Pro R$ 59,90**,
  **Premium R$ 109,90**. Valores por período (arredondamento para o centavo, meio
  para cima), sujeitos à confirmação final de Rafa:

| Período | Pro (total) | Pro (por mês) | Premium (total) | Premium (por mês) |
|---|---|---|---|---|
| Mensal | R$ 59,90 | R$ 59,90 | R$ 109,90 | R$ 109,90 |
| 3 meses | R$ 175,21 | R$ 58,40 | R$ 321,46 | R$ 107,15 |
| 6 meses | R$ 341,43 | R$ 56,91 | R$ 626,43 | R$ 104,41 |
| 1 ano | R$ 610,98 | R$ 50,92 | R$ 1.120,98 | R$ 93,42 |

- **Plano de 9 meses descartado:** o Asaas não tem ciclo de 9 meses
  (ciclos: `WEEKLY`, `BIWEEKLY`, `MONTHLY`, `BIMONTHLY`, `QUARTERLY`,
  `SEMIANNUALLY`, `YEARLY`). Todos os períodos acima renovam automaticamente.
- **Pendentes:** formas de pagamento
  (só cartão ou cartão + Pix); dias de tolerância de atraso; nota fiscal automática.
- Regras de troca de plano já vigentes ([política F4, seção 12](PLANOS-F4-POLITICAS-E-FASES-20261103.md)):
  ativação só após pagamento confirmado; downgrade e cancelamento valem no
  vencimento, sem cortar o período já pago; Premium→Pro pausa campanhas
  acima de 2 por perfil até o titular escolher.

## 2. Como o Asaas funciona (documentação oficial, lida em 10/11/2026)

- API REST `https://api-sandbox.asaas.com/v3` (testes) e `https://api.asaas.com/v3`
  (produção), chave no header `access_token`, `User-Agent` obrigatório para contas
  novas. Chaves de sandbox e de produção são diferentes; sandbox é outra conta.
- **Checkout hospedado** (`POST /v3/checkouts`, `chargeTypes: ["RECURRENT"]` +
  objeto `subscription` com `cycle` e `nextDueDate`): o cliente paga na página do
  Asaas; o cartão nunca passa pelo nosso servidor. Expira entre 10 e 1440 min.
  `externalReference` liga o checkout ao nosso pedido. Ao pagar, o Asaas cria a
  assinatura e gera as cobranças de cada ciclo; no cartão, cobra no vencimento.
- **Confirmação só por webhook** (`CHECKOUT_PAID`, `SUBSCRIPTION_CREATED`,
  `PAYMENT_CONFIRMED`/`PAYMENT_RECEIVED`); a `successUrl` é só redirecionamento.
- **Webhook:** entrega *at least once* (guardar `id` do evento como chave única),
  token próprio no header `asaas-access-token`, responder 200 rápido e processar
  depois. Após 15 falhas seguidas a fila pausa; eventos parados há mais de 14 dias
  são apagados.
- **Assinatura:** `PUT /v3/subscriptions/{id}` altera valor/ciclo (padrão: só
  cobranças futuras); `PUT .../creditCard` troca o cartão; `status=INACTIVE`
  pausa; `DELETE` encerra e apaga cobranças pendentes/vencidas.
- **Não confirmado:** se o checkout recorrente aceita Pix (a página mostra só
  cartão) — testar no sandbox. Taxas e prazos de repasse não pesquisados.

## 3. Arquitetura proposta

- **Segredos (Render, nunca no código nem no navegador):** `ASAAS_API_KEY`,
  `ASAAS_API_URL`, `ASAAS_WEBHOOK_TOKEN`. Staging = sandbox; produção = conta real.
- **Banco (migração aditiva, RLS sem acesso do navegador, só `service_role`):**
  - `plan_prices` — preço mensal por plano e desconto por período, editável pelo
    ADMIN com auditoria (o valor cobrado é sempre calculado no servidor).
  - `billing_customers` — conta ↔ `customer` do Asaas.
  - `billing_subscriptions` — conta, plano, período, `asaas_subscription_id`,
    status, `current_period_end`, troca agendada para o vencimento.
  - `billing_checkouts` — pedido interno (`externalReference`), checkout do Asaas, status.
  - `billing_payments` — histórico de cobranças (status, valor, vencimento).
  - `billing_webhook_events` — `id` do evento único, payload, processado em, erro.
- **API:** `GET /billing/plans` (preços calculados), `POST /billing/checkout`
  (valida dados do titular em `account_billing_identity`, cria cliente e checkout,
  devolve link), `GET /billing/subscription`, `POST /billing/subscription/cancel`,
  `POST /billing/subscription/change`, `POST /billing/webhook` (público, token).
- **Mudança de plano:** só o processador do webhook altera `users.plan_tier`,
  dentro de transação; navegador nunca decide plano. ADMIN segue sem cota.
- **Conciliação:** job periódico consulta assinaturas ativas no Asaas para cobrir
  webhook perdido; alerta ao ADMIN se a fila do webhook pausar.

## 4. Fases (cada uma: staging → teste de Rafa)

1. **Base:** cliente HTTP do Asaas, variáveis no Render staging, migração, tabela
   de preços, registro do webhook via API, testes.
2. **Contratar:** tela de planos com os 4 períodos e descontos, botão de assinar,
   checkout hospedado, telas de retorno ("aguardando confirmação").
3. **Webhook e ativação:** processamento idempotente; pagamento confirmado ativa o
   plano; atraso respeita tolerância; estorno e chargeback voltam para Free.
4. **Gerenciar:** "Minha assinatura" — plano, próximo vencimento, histórico,
   trocar cartão, cancelar, trocar plano/período no vencimento.
5. **Operação e legal:** conciliação, painel ADMIN, atualização de Termos e
   Política de Privacidade (dados enviados ao Asaas).
6. **Produção:** com autorização de Rafa, chave de produção no Render e webhook de
   produção.

## 5. O que Rafa precisa fornecer

- Conta **sandbox** em `sandbox.asaas.com` e a chave de API dela cadastrada por
  ele no Render (serviço staging) como `ASAAS_API_KEY` — nunca no chat.
- Respostas aos pendentes da seção 1 (formas de pagamento, tolerância, nota fiscal).
