# Shopee Open Platform — regularização do cadastro de desenvolvedor

**Data:** 07/11/2026 · **Alvo:** Auto Orbital / Raffa Studio Produções · **Fonte operacional:** três capturas fornecidas por Rafa da conta autenticada em `open.shopee.com` (leitura visual, **sem acesso ao motivo interno da rejeição**). **Destino declarado pelo proprietário:** Shopee Vídeo para **criadores/afiliados**, não uma loja vendedora. **Fase atual:** regularização documental de conta; a implementação no Auto Orbital **fica pausada** até finalização da análise Shopee.

> Não anexar capturas contendo dados pessoais ao repositório, não copiar campos de contato/endereço para esta documentação e não registrar senhas/Partner Key/tokens. Nenhum documento da conta foi criado, substituído, excluído ou reenviado por esta tarefa.

## 1. Inventário real do console

| Ordem | Tela/campo | Estado observado em 07/11 | O que falta decidir/fazer |
| --- | --- | --- | --- |
| **1 — Rejeitado** | `Personal Center → Account Information → Security Reports & Certifications Information` | **Penetration Test Report — Rejected**, expiração `-`. Há arquivo PDF submetido com título visível de **relatório técnico de avaliação de segurança do Auto Orbital**. **Motivo não aparece nas capturas**. | Clicar no **lápis de edição** para inspecionar observações/motivo, tipo de documento, regras e opções. Se não houver justificativa, consultar `Ticket System → My Tickets` e abrir pedido de esclarecimento. **Não reenviar o mesmo documento nem apagar evidências sem entender a recusa.** |
| **2 — Pendente** | `Supporting Documents Information` | **Pending Upload**. `Uploaded Signed Declaration`: `No Upload`; `Live Product Screenshots`: `No Upload`; `Website URL of Live Product`: `-`; `Username of Live Test Account`: `-`; `Password of Live Test Account`: `-`. | Após o caso rejeitado estar esclarecido, confirmar exigências de cada campo e preparar documentos verídicos, imagens de produto funcional e conta de teste exclusiva com dados sintéticos. Senha só pelo **canal oficial seguro**, jamais por chat/documento Git. |
| **3 — Ainda não iniciado** | `App Management → App List` | Página vazia: **Haven't created an application?** / botão `Create an APP`. | Criar somente depois de alinhar categoria, escopo, política e permissão da Shopee **para feed de criadores afiliados brasileiros**. O console de desenvolvedor é diferente da **Affiliate Open API GraphQL** existente no Auto Orbital. |

**Nota sobre status:** `Rejected` é um fato do console, **não é prova de vulnerabilidade do site** nem de que a submissão é obrigatória para este caso. `Pending Upload` não significa que a Shopee já solicitou todas as evidências para um aplicativo com escopos aprovados. A lista vazia é evidência de **nenhum aplicativo cadastrado nessa conta**, não prova que qualquer outra conta de afiliado esteja desconectada.

## 2. Primeiro resolver a rejeição — decisão de conformidade

1. **Ler o motivo exato:** abrir o lápis do relatório rejeitado **sem salvar**, buscar `Reason`, `Review Comment`, `Rejection Remark`, exigência de fornecedor, validade, escopo, tipo de auditoria ou comunicado. Capturar **somente** o texto/status; ocultar endereço, documento empresarial, senha e contatos. Procurar também notificações e `My Tickets` na Open Platform.
2. **Verificar se o pentest se aplica ao cadastro:** o objetivo é o feed de afiliados do Brasil, **sem demanda identificada de PII de compradores**. As regras de pentest identificadas em materiais de Open Platform incluem situações específicas de ISVs/mercados e acesso a dados sensíveis; **não é correto concluir que toda integração brasileira de afiliados exige pentest independente**. A Shopee deve confirmar os critérios da **categoria de desenvolvedor, serviço/país e dados solicitados** antes de qualquer contratação.
3. **Classificar o PDF enviado corretamente:** testes automatizados, relatórios internos, ZAP baseline, SBOM e parecer técnico redigido pela equipe **não são automaticamente um teste de intrusão independente**. O arquivo submetido não foi disponibilizado para auditoria nesta tarefa; a imagem do título não permite afirmar seu conteúdo/metodologia/autor. **Não falsificar emissor, assinatura, certificação ou resultado** e não trocar somente o nome do PDF para `Penetration Test Report`.
4. **Tratar conforme resposta oficial:**
   - Se o campo foi preenchido **voluntariamente/por engano**, solicitar ao suporte instrução para corrigir a classificação/registro, **sem apagar histórico por conta própria**.
   - Se houver **relatório independente real** e a Shopee apontar problema formal (arquivo, escopo, data), corrigir com o assessor responsável e reapresentar conforme instrução.
   - Se for **exigido novo pentest independente**, levantar escopo e critérios e **pedir aprovação expressa de Rafa antes de contratar, executar teste externo ou gastar**. O teste só pode ser conduzido por pessoal autorizado em ambiente/escopo aprovado.
5. **Fechamento da fase 1:** registrar comentário oficial, elegibilidade, ação tomada, protocolo e status final. Passar à fase 2 quando a rejeição estiver esclarecida/regularizada — **não inventar que foi aprovada** se a Shopee dispensar o documento em vez de aprová-lo.

### Solicitação sugerida ao suporte Shopee (se o formulário não mostrar o motivo)

> Hello Shopee Open Platform Support. We are developing **Auto Orbital**, a Brazil-based SaaS for **Shopee creator/affiliate content**. In **Personal Center → Account Information → Security Reports & Certifications Information**, our submitted **Penetration Test Report** currently shows **Rejected**, with no visible rejection reason. Could you please provide the exact rejection reason and correction requirements? Is a third-party penetration test report **mandatory for our Brazil-based developer category and intended affiliate video service**, considering we **do not intend to request buyer PII access** for this integration? If the report category is not applicable, what is the proper way to rectify this submission without losing the audit trail? We will only resubmit genuine evidence according to your instructions. Thank you.

**Essa mensagem é um modelo, ainda não enviada.** Ajustar qualquer afirmação de escopo de dados se os serviços solicitados mudarem. Nunca anexar segredos ou arquivos de clientes a ticket.

## 3. Depois regularizar `Supporting Documents Information`

| Item do portal | Preparação segura | Critério de aceite/pendência |
| --- | --- | --- |
| `Uploaded Signed Declaration` | Abrir **Edit** e obter o **modelo oficial** exigido; somente o representante legal assina dados verdadeiros, sem assinatura gerada por IA ou declaração de capacidade não existente. | Modelo, conteúdo, signatário e exigência para a categoria **a confirmar no portal**. |
| `Live Product Screenshots` | Capturas atuais do Auto Orbital em `staging`/produção de fluxo realmente funcionando (login de teste, catálogo Shopee/links, separação de perfis, tela de segurança); **sem clientes, tokens, senha ou dados sensíveis**. | Mostrar somente recursos implantados e acessíveis ao revisor; **não declarar Shopee Vídeo ativo**. |
| `Website URL of Live Product` | URL HTTPS real da aplicação selecionada para avaliação, confirmada acessível sem erro e com política de privacidade/termos. | Verificar com a Shopee se quer ambiente **produção** ou teste, e se acesso autenticado é exigido. Não usar URL inventada. |
| `Username/Password of Live Test Account` | Conta dedicada ao revisor, menor privilégio possível, dados sintéticos, sem acesso ADMIN nem recursos reais de clientes. Segredo exclusivo, rotacionável e com prazo/remoção definidos. | Criar/entregar **somente depois** de instrução e autorização, **somente pelo console oficial**; nunca reutilizar credenciais pessoais, de suporte ou senhas de outro serviço. |

**Dependência:** algumas provas do produto só podem ser avaliadas depois de existir aplicativo/serviço aprovado. Se o formulário pedir isso antes, perguntar à Shopee quais evidências preliminares aceitam, preservando a sequência preferida por Rafa: rejeitados → pendentes → app. Não fabricar vídeo de uma integração ainda bloqueada.

## 4. Por último — criar o aplicativo correto

- Registrar a categoria correta **depois** de confirmar no suporte se a Open Platform **autoriza** criar/publicar no **feed Shopee Vídeo para criadores afiliados brasileiros**; a API `Video Management` não é automaticamente a API Affiliate GraphQL.
- A aprovação da conta de desenvolvedor e dos documentos **não concede por si só** permissão de vídeo, acesso a dados, OAuth de afiliado, publicação ou analytics.
- Manter App/Partner secrets somente no backend, por ambiente; usuário final terá OAuth por `user_id + profile_id` apenas quando autorizado. Não ativar uploads reais para demonstrar integração sem autorização.
- O plano técnico de futuro envio, associação de até seis `itemId` e leitura de métricas por vídeo permanece em [SHOPEE-VIDEO-AFILIADOS-GATE-20261107](SHOPEE-VIDEO-AFILIADOS-GATE-20261107.md). O código `apis/shopee_video.py` **segue desativado**.

## 5. Próxima interação com Rafa

**Uma ação de cada vez:** clicar no **ícone de lápis** do `Penetration Test Report` com status `Rejected` e enviar captura da janela inteira **sem salvar**, ocultando dados pessoais. Se não existir comentário de rejeição, mostrar `My Tickets` ou responder que não há observações; então utilizar a solicitação de esclarecimento acima pelo suporte oficial. **Não abrir app, editar pendências, reenviar PDF, excluir registro ou contratar pentest nesta etapa.**

## 6. Evidências, limites e fontes

- Capturas de 07/11/2026 (usuário, sessão de Shopee Open Platform): status `Rejected`, `Pending Upload`, `No Upload`, campos vazios e `App List` sem aplicativo. **Não foram verificadas respostas de rede, permissão interna, exigência de campos ou motivo de rejeição.**
- [Shopee Open Platform — Developer Guide](https://open.shopee.com/developer-guide/736) e [Help Center oficial — Data Sharing Agreement](https://help.shopee.sg/portal/4/article/173516). O contrato citado trata de cenário específico de compartilhamento de dados/logística, **não** comprova que a exigência se aplique ao afiliado brasileiro.
- Histórico de política reproduzido por arquivo secundário: [mudança de submissão no console em dezembro de 2025](https://kgcang.com/library/doc/sources%2Fshopee%2Fprofile.shopee.announcements%2Fdeveloper-policy%2F2025%2F2025-12-29-policy-update-migration-of-penetration-test-report-submission-to-open-platform); mencionava exigência para determinados ISVs com acesso PII na Tailândia. **Verificar diretamente com a Shopee antes de aplicar a outro mercado.**
- Internos: [SHOPEE-VIDEO-VALIDACAO](SHOPEE-VIDEO-VALIDACAO.md), [SEGURANCA-PENDENCIAS](SEGURANCA-PENDENCIAS-20261031.md), [TASK](TASK.md), [GUIA-MESTRE-IA](GUIA-MESTRE-IA.md), `AGENTS.md`.

**Governança:** documentação somente; `VERSION=3.4.0`, sem bump. Sem alteração de produção/`main`, contas Shopee, Supabase compartilhado, credenciais, migrations, duas rotinas `pg_cron`, `pg_net`, mídia, scheduler, publicação, despesa ou contratação. Gatilho de SMTP não acionado: não há evidência de domínio próprio **registrado e configurado** no site.
