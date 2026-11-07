# Shopee Open Platform — regularização do cadastro de desenvolvedor

**Data:** 07/11/2026 · **Alvo:** Auto Orbital / Raffa Studio Produções · **Fonte operacional:** capturas fornecidas por Rafa da conta autenticada em `open.shopee.com`, incluindo a notificação de perfil aprovado, o Task Center e os detalhes da recusa (caso 1750). **Destino declarado pelo proprietário:** Shopee Vídeo para **criadores/afiliados**, não uma loja vendedora. **Fase atual:** informações organizadas e **em espera por decisão de Rafa**; integração Shopee Vídeo continua pausada.

> Não anexar capturas contendo dados pessoais ao repositório, não copiar campos de contato/endereço para esta documentação e não registrar senhas/Partner Key/tokens. Nenhum documento da conta foi criado, substituído, excluído ou reenviado por esta tarefa.

## 0. Atualização confirmada — perfil aprovado, caso 1750 e Task Center (07/11/2026)

| Evidência visual fornecida por Rafa | Constatação | Limite da conclusão |
| --- | --- | --- |
| `Notification Center → My Notifications`, mensagem `[Open Platform] Profile Verification Successful` datada **03/11/2026 18:29** | **Perfil de desenvolvedor verificado**; a mensagem diz `You can now start developing on the Shopee Open Platform.` e apresenta criação de app, sandbox, autorização e whitelist de IPs como próximos passos. | **Não comprova** aprovação de qualquer aplicativo, API de vídeo/afiliados ou relatório de segurança. O **App Type** determina endpoints disponíveis. |
| `Task Center → My Tasks`, captura de 07/11/2026 | **0** obrigatórias atrasadas; **0** obrigatórias em sete dias; **0** obrigatórias em andamento; **0** recomendadas em andamento. A lista `In Progress` aparece vazia. | Ausência de tarefa visível **não dispensa** controles exigidos na futura criação/avaliação de app. |
| `Personal Center → Account Information → Edit Security Reports & Certifications Information` | **Case ID 1750**, `Rejected`, `Case Update Time: 2026-11-04 03:32`. Comentário literal da Shopee: **“Not a pentest: document/code review only, no active testing; findings R-01...R-07 have no screenshots, requests or tool output (links only).”** | Foi **rejeitada a qualificação do documento como pentest** por ausência de execução ativa e evidências nos achados; isso **não prova** falhas exploráveis no Auto Orbital e **não esclarece** se o pentest é obrigatório para a categoria brasileira de afiliados. |

**Interpretação:** o perfil foi aprovado **antes** da atualização da rejeição do relatório; aparentemente a recusa **não impediu a verificação do perfil**, mas não há confirmação de que autorize futuras permissões de app. O painel de tarefas zerado também não prova dispensa formal. **Não reenviar o mesmo relatório ou inventar screenshots, requisições e saídas de ferramentas.** Caso haja exigência de pentest, definir escopo autorizado, execução real e evidências reproduzíveis; eventual auditor externo ou gasto requer aprovação expressa.

## 1. Inventário real do console

| Ordem | Tela/campo | Estado observado em 07/11 | O que falta decidir/fazer |
| --- | --- | --- | --- |
| **1 — Rejeitado** | `Personal Center → Account Information → Security Reports & Certifications Information` | **Penetration Test Report — Rejected**, expiração `-`, **Case ID 1750**, motivo explícito de que foi apenas `document/code review`, sem testes ativos nem provas dos achados `R-01...R-07`. | **Motivo já identificado.** Pedir ao suporte confirmação de obrigatoriedade do pentest para criadores/afiliados BR, de efeitos da rejeição no app e da regularização correta do caso. **Não reenviar o mesmo PDF, excluir histórico ou contratar teste sem resposta e aprovação.** |
| **2 — Pendente** | `Supporting Documents Information` | **Pending Upload**. `Uploaded Signed Declaration`: `No Upload`; `Live Product Screenshots`: `No Upload`; `Website URL of Live Product`: `-`; `Username of Live Test Account`: `-`; `Password of Live Test Account`: `-`. | Após o caso rejeitado estar esclarecido, confirmar exigências de cada campo e preparar documentos verídicos, imagens de produto funcional e conta de teste exclusiva com dados sintéticos. Senha só pelo **canal oficial seguro**, jamais por chat/documento Git. |
| **3 — Ainda não iniciado** | `App Management → App List` | Página vazia: **Haven't created an application?** / botão `Create an APP`. | Criar somente depois de alinhar categoria, escopo, política e permissão da Shopee **para feed de criadores afiliados brasileiros**. O console de desenvolvedor é diferente da **Affiliate Open API GraphQL** existente no Auto Orbital. |

**Nota sobre status:** `Rejected` é um fato do console, **não é prova de vulnerabilidade do site** nem de que a submissão é obrigatória para este caso. `Pending Upload` não significa que a Shopee já solicitou todas as evidências para um aplicativo com escopos aprovados. A lista vazia é evidência de **nenhum aplicativo cadastrado nessa conta**, não prova que qualquer outra conta de afiliado esteja desconectada.

## 2. Primeiro resolver a rejeição — decisão de conformidade

1. **Motivo encontrado em 07/11:** o caso **1750** informa expressamente **“Not a pentest: document/code review only, no active testing; findings R-01...R-07 have no screenshots, requests or tool output (links only).”** A leitura do lápis está **concluída**; não há necessidade de nova inspeção dessa tela. A decisão pendente é saber **se um pentest é exigido para a categoria e serviços pretendidos**. Não copiar relatórios sensíveis para issues/tickets públicos.
2. **Verificar se o pentest se aplica ao cadastro:** o objetivo é o feed de afiliados do Brasil, **sem demanda identificada de PII de compradores**. As regras de pentest identificadas em materiais de Open Platform incluem situações específicas de ISVs/mercados e acesso a dados sensíveis; **não é correto concluir que toda integração brasileira de afiliados exige pentest independente**. A Shopee deve confirmar os critérios da **categoria de desenvolvedor, serviço/país e dados solicitados** antes de qualquer contratação.
3. **Classificar o PDF enviado corretamente:** testes automatizados, relatórios internos, ZAP baseline, SBOM e parecer técnico redigido pela equipe **não são automaticamente um teste de intrusão independente**. O arquivo submetido não foi disponibilizado para auditoria nesta tarefa; a imagem do título não permite afirmar seu conteúdo/metodologia/autor. **Não falsificar emissor, assinatura, certificação ou resultado** e não trocar somente o nome do PDF para `Penetration Test Report`.
4. **Tratar conforme resposta oficial:**
   - Se o campo foi preenchido **voluntariamente/por engano**, solicitar ao suporte instrução para corrigir a classificação/registro, **sem apagar histórico por conta própria**.
   - Se houver **relatório independente real** e a Shopee apontar problema formal (arquivo, escopo, data), corrigir com o assessor responsável e reapresentar conforme instrução.
   - Se for **exigido novo pentest independente**, levantar escopo e critérios e **pedir aprovação expressa de Rafa antes de contratar, executar teste externo ou gastar**. O teste só pode ser conduzido por pessoal autorizado em ambiente/escopo aprovado.
5. **Fechamento da fase 1:** registrar comentário oficial, elegibilidade, ação tomada, protocolo e status final. Passar à fase 2 quando a rejeição estiver esclarecida/regularizada — **não inventar que foi aprovada** se a Shopee dispensar o documento em vez de aprová-lo.

### Mensagem pronta para Shopee Open Platform Support — **rascunho não enviado**

> Hello Shopee Open Platform Support,
>
> Our developer profile was successfully verified on November 3, 2026, and we currently have no mandatory tasks in the Task Center.
>
> However, our Penetration Test Report (**Case ID: 1750**) was rejected because it was classified as a documentation/code review without active testing evidence.
>
> We are developing **Auto Orbital**, a Brazil-based application intended to serve **Shopee creators and affiliates**, including affiliate video workflows and product association, subject to API availability and approval.
>
> Could you please clarify:
> 1. Is an **independent penetration test mandatory** for our developer category and intended services in Brazil?
> 2. Is the rejected report **currently blocking application creation, approval, or access to specific APIs**?
> 3. If a penetration test is required, what exact **scope, evidence, testing standard, and assessor qualifications** are expected?
> 4. If it is not required for our application category, how should we properly **resolve or close Case 1750**?
>
> Thank you.

**Não enviada; não há número de ticket novo.** Quando Rafa retomar, abrir `Ticket System → Raise Ticket`, verificar a categoria correta e revisar a mensagem antes de enviar. Nunca anexar credenciais, dados de clientes ou artefatos de testes não autorizados. Não afirmar que qualquer API de afiliados/vídeos foi aprovada.

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

**A pedido de Rafa, trabalho pausado e preparado para retomada posterior.** O motivo da rejeição (caso 1750) já foi identificado, o perfil de desenvolvedor está verificado e o Task Center mostra zero obrigações em andamento. Ao retomar: abrir `Ticket System → Raise Ticket`, escolher a categoria adequada e, **com autorização de Rafa**, enviar o rascunho acima para esclarecer a exigência e como regularizar o relatório. Depois resolver documentos realmente exigidos; criar o app com **App Type correto** somente com requisitos e permissão de vídeo/afiliados confirmados. **Nenhum ticket enviado e nenhuma ação na conta executada nesta etapa.**

## 6. Evidências, limites e fontes

- Capturas de 07/11/2026 (usuário, sessão de Shopee Open Platform): perfil `Verification Successful` (notificação de 03/11), Task Center com quatro contadores zerados, caso **1750** com justificativa textual de rejeição (04/11), documentos `Pending Upload` e `App List` sem aplicativo. **Não foram verificadas respostas internas de API, exigência de pentest para afiliado BR, liberação de escopos ou envio de ticket.**
- [Shopee Open Platform — Developer Guide](https://open.shopee.com/developer-guide/736) e [Help Center oficial — Data Sharing Agreement](https://help.shopee.sg/portal/4/article/173516). O contrato citado trata de cenário específico de compartilhamento de dados/logística, **não** comprova que a exigência se aplique ao afiliado brasileiro.
- Histórico de política reproduzido por arquivo secundário: [mudança de submissão no console em dezembro de 2025](https://kgcang.com/library/doc/sources%2Fshopee%2Fprofile.shopee.announcements%2Fdeveloper-policy%2F2025%2F2025-12-29-policy-update-migration-of-penetration-test-report-submission-to-open-platform); mencionava exigência para determinados ISVs com acesso PII na Tailândia. **Verificar diretamente com a Shopee antes de aplicar a outro mercado.**
- Internos: [SHOPEE-VIDEO-VALIDACAO](SHOPEE-VIDEO-VALIDACAO.md), [SEGURANCA-PENDENCIAS](SEGURANCA-PENDENCIAS-20261031.md), [TASK](TASK.md), [GUIA-MESTRE-IA](GUIA-MESTRE-IA.md), `AGENTS.md`.

**Governança:** documentação somente; `VERSION=3.4.0`, sem bump. Sem alteração de produção/`main`, contas Shopee, Supabase compartilhado, credenciais, migrations, duas rotinas `pg_cron`, `pg_net`, mídia, scheduler, publicação, despesa ou contratação. Gatilho de SMTP não acionado: não há evidência de domínio próprio **registrado e configurado** no site.
