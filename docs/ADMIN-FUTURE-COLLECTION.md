# Plano de coleta futura — proposta, sem rastreamento ativado

Nenhum evento, cookie, heartbeat, pixel, SDK de analytics ou cobrança foi ativado por este trabalho. Esta especificação define uma primeira versão mínima para revisão antes da implementação. A autenticação existente não é alterada.

## Contrato de privacidade

O navegador administrativo recebe contagens, períodos, durações agregadas e categorias aprovadas. Senhas, tokens, hashes, IPs, coordenadas, endereços, URLs completas e identificadores individuais não entram no contrato analítico. Identificadores internos necessários para autenticação, deduplicação e cobrança ficam restritos ao servidor e não são convertidos em hashes para exposição no painel.

Dados ligados internamente a uma conta continuam sendo dados vinculáveis; não devem ser chamados de anônimos. A finalidade, a informação ao usuário, a base aplicável e a retenção precisam ser revisadas antes de ativar qualquer coleta nova. Sem uma decisão aprovada, o indicador continua “não coletado”.

## Indicadores propostos

| Indicador | Fonte mínima | Definição e limite | Exibição |
|---|---|---|---|
| Origem dos cadastros | Categoria de campanha aprovada enviada no cadastro bem-sucedido | Allowlist de `source`/`medium` e nome público de campanha; rejeitar texto arbitrário, URLs e query strings. Ausência vira “Não informado”, nunca inferir “direto”. | Contagem por categoria e período; sem linha por usuário. |
| Cadastros e exclusões históricos | Operação concluída no backend | Incrementar contador diário transacional e idempotente, com data de início da coleta. Exclusão mantém somente o agregado necessário; não tentar recuperar contas apagadas. | Série diária de eventos concluídos, distinta do indicador atual de contas sobreviventes. |
| Contas pagantes | Webhook de cobrança verificado | Assinatura verificada, evento deduplicado e pagamento confirmado com acesso vigente. Não deduzir pagamento de `plan_tier`, trial ou plano atribuído manualmente. | Pagantes, gratuitas, trial e situação não confirmada separados. |
| Tempo de uso ativo | Sinal de atividade da aplicação, somente após revisão/ativação | Contabilizar no máximo 60 segundos por minuto, apenas com página visível e interação recente; parar após 5 minutos sem interação. É estimativa de atividade, não tempo de trabalho ou presença exata. | Minutos agregados e média com denominador informado; nunca histórico individual. |
| Região | Declaração opcional de país/UF | Não consultar IP, GPS, endereço do perfil nem serviço de geolocalização. Campos opcionais com categorias limitadas e possibilidade de remover a declaração. | Somente grupos com pelo menos 5 contas; suprimir também totais complementares que permitam deduzir grupos pequenos. Sem mapa enquanto não houver base suficiente. |

## Fluxo mínimo no servidor

1. Cadastro e exclusão: atualizar os contadores somente depois do sucesso da operação, na mesma transação quando possível. Repetições não duplicam o agregado. Data e fuso dos contadores: Brasília; armazenamento de instantes em UTC.
2. Origem: validar categorias no backend. Não guardar `document.referrer`, URL de entrada ou parâmetros livres. Não registrar payload de campanha em logs.
3. Atividade: o servidor deriva a conta da sessão autenticada. Um bucket interno por conta/minuto limita e deduplica os segundos. Impedir escrita direta pelo cliente nas tabelas de agregados e rejeitar durações fora do intervalo. Não enviar identificador de conta no payload do heartbeat.
4. Cobrança: registrar o mínimo necessário no domínio de pagamentos, validar assinatura e idempotência antes de mudar o estado. Reembolso, expiração, cancelamento e falha de pagamento têm transições explícitas; nunca ligar cobrança real como parte de testes.
5. O endpoint ADMIN lê agregados e aplica supressão de grupos pequenos no servidor. Nenhuma consulta administrativa oferece drill-down por indivíduo.

## Retenção proposta para aprovação

Buckets técnicos de atividade: até 7 dias para deduplicação/diagnóstico; depois, somente totais diários. Agregados analíticos: janela inicial de 90 dias, com expurgo programado e teste de exclusão. Categorias de origem e região vinculadas à conta seguem a política de remoção aprovada; não preservar cadastros detalhados após apagar a conta. Registros de cobrança exigem política própria antes da ativação, sem copiar dados financeiros para analytics.

Esses prazos são propostas operacionais, não afirmações de obrigação legal nem aprovação para iniciar coleta.

## Ordem de implementação futura

1. Aprovar finalidade, informação ao usuário, retenção e unidade de cobrança (conta ou perfil). Proposta inicial: consolidar o indicador de pagantes por conta, sem contar o mesmo usuário duas vezes.
2. Contadores transacionais de cadastro/exclusão e categorias de origem; migração e testes em banco descartável.
3. Cobrança exclusivamente em modo teste, com eventos repetidos, atrasados, inválidos, cancelados e reembolsados.
4. Tempo de atividade apenas após revisão do fluxo e da informação ao usuário; testes de aba oculta, inatividade, duas abas, retries e desconexão.
5. Região opcional por último, somente se houver utilidade e tamanho de grupos suficiente.

## Critérios para ativar

- Nenhum segredo, ID individual ou texto livre chega à API de analytics.
- Contagens consistentes sob retries, concorrência, exclusão e mudança de perfil.
- Comparações identificam período atual incompleto e distinguem ausência de coleta de zero real.
- RLS/roles testados com acesso negado para usuários comuns e clientes diretos.
- Expurgo, remoção e supressão de grupos pequenos testados; sem inferência por totais complementares.
- Inspeção de rede confirma ausência de terceiros, pixels e payloads extras antes da ativação.
- Aprovação humana antes de migração real, instrumentação nova ou cobrança.
