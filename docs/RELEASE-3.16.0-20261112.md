# Auto Orbital 3.16.0 — Release MINOR (preparação)

**Data:** 12/11/2026 (UTC)
**Autorização:** Rafa pediu a promoção `staging → main` ("dando verde quero a promoção para a main") depois de testar na staging.
**Versão:** 3.15.0 → 3.16.0 (**MINOR**, conforme `docs/RULES.md`).

## 1. Escopo (PRs #441 a #456 na staging)

- **Pagamentos Asaas** (`docs/PAGAMENTOS-ASAAS-PLANO-20261110.md`): preços e períodos calculados no servidor (Pro R$ 59,90; Premium R$ 109,90; 1, 3, 6 meses e 1 ano com 0%, 2,5%, 5%, 15%); checkout hospedado recorrente no cartão; **Pix via Pix Automático** (QR Code na página `/planos`, cronômetro de 1 h); webhook idempotente; job de conciliação; painel ADMIN `/admin/billing`.
- **Cliente:** página `/planos` (planos, pagamento, minha assinatura, tabela "Planos e limites" movida das Configurações, cancelamento de plano, guia de teste do sandbox) e botões de upgrade em todo o site e na apresentação.
- **Cadastro:** validação ao vivo de CPF (dígitos verificadores), e-mail, nome e senha (mínimo 8); servidor recusa e-mail malformado.
- **Visual:** etiqueta de plano do cabeçalho alinhada; login com animação em 60% e formulário em 40%.
- **CI:** job da API fixado em `ubuntu-24.04`.
- **Operação (banco compartilhado, já aplicada a pedido de Rafa; ver `docs/operations/`):** cron de despertar só antes de publicações de produção com log (`admin_wake_log`); migração dos agendamentos da staging para a produção; reset do histórico de posts.

## 2. Comportamento em produção após o deploy

- **Contratação desligada** (sem `ASAAS_API_KEY`/`ASAAS_WEBHOOK_TOKEN` no Render de produção; `ASAAS_API_URL` padrão aponta para o sandbox). Nada é cobrado e nenhum dado vai ao Asaas.
- Banco de produção tem 3 contas, todas no plano Free; nenhuma conta paga é afetada. Sem assinatura, o botão "Cancelar plano" só aparece para conta com plano pago (nenhuma hoje); em produção responderia "Cobrança em fase de testes" até a chave existir.
- Scheduler da produção ganha o job `billing_asaas` (a cada 10 min); sem chave ele não faz nada.

## 3. Não validado e pendências

- Pagamento de ponta a ponta (cartão e Pix) com mudança de plano, formato real dos avisos do Pix Automático e elegibilidade da conta Asaas: **não validados**.
- Para **abrir a contratação em produção** (só com autorização de Rafa): chave Asaas de produção, `ASAAS_API_URL` de produção, `ASAAS_WEBHOOK_TOKEN`, webhook de produção registrado no painel ADMIN, atualização de Termos e Política de Privacidade (dados enviados ao Asaas) e cadastro fiscal para NFS-e.
- Aviso de "pagamento pendente" no sino, troca de plano com assinatura aberta e pausa de campanhas no downgrade: não implementados.
- Primeiras execuções reais de agendamentos na produção (recorrência 12/11 12:00 UTC; campanha 12/11 13:00 UTC): ainda não observadas.

## 4. Evidências

Preenchidas após o deploy (PR de promoção, CI, gate SemVer, deploy Render, logs de boot) em registro posterior.
