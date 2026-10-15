# Métricas administrativas

`/admin/overview` e `GET /admin/metrics?days=30` exigem ADMIN. A resposta contém somente agregados e não contém senhas, hashes, IPs, identificadores de conta, serviço ou instância.

## Ativação após revisão

1. Revisar e aplicar `database/migrations/051_admin_metrics_snapshot.sql` pelo processo de migrações do projeto. A função é invoker, com execução restrita a `service_role`. Nesta tarefa somente seu SELECT foi executado, sem DDL ou alteração de dados.
2. Usar as variáveis de conexão Supabase já existentes no backend. Não enviar chaves ao frontend.
3. Configurar `RENDER_METRICS_API_KEY` somente no servidor, com uma chave autorizada a consultar o serviço, e `RENDER_SERVICE_ID` com o serviço a monitorar. Não usar credenciais dos plugins no aplicativo. O serviço de referência confirmado pelo responsável é `shopee-bot` de produção; `shopee-bot-staging` é outro ambiente.
4. Validar com uma conta ADMIN e uma USER: a segunda deve receber 403 antes de consultar qualquer provedor.

O endpoint coleta CPU, memória, limites de CPU/memória e tráfego do Render em 24 horas, resolução de uma hora. Mostra o horário de cada amostra; métricas ausentes ficam indisponíveis. O painel consulta a cada minuto. A conexão autorizada dos plugins do Codex serve para inspeção e não configura automaticamente as credenciais do backend.

## Dados e limites

- Contas atuais e planos do perfil principal. Planos não comprovam pagamento.
- Cadastros de contas ainda existentes no período; não reconstitui contas excluídas.
- Exclusões preservadas na auditoria. Autoexclusões antigas podem estar ausentes por uma FK corrigida neste branch; nenhum histórico foi reconstruído.
- Ativos: requisições autenticadas com resposta menor que 400 nos últimos cinco minutos. Não é presença exata. Sem registro de requisições, fica indisponível.
- Requisições, erros e latência média/p95 são do histórico disponível no aplicativo.
- Supabase: tamanho do banco, conexões e limite; não equivale a consumo total de disco, storage ou faturamento. Latência da RPC é medida separadamente.
- Origem, tempo de sessão, localização e pagamento confirmado não são coletados atualmente.

Amostras ausentes não viram zero. As curvas unem observações, preservam os valores medidos e usam a posição temporal das amostras Render. Tabelas expansíveis oferecem os valores exatos.

## Verificação real em 15/10/2026

Consultas somente leitura confirmaram as colunas e executaram o SELECT de agregação nos períodos 7/30/90 dias. No serviço Render de produção havia memória, limites e tráfego; uso de CPU e HTTP vieram sem amostras na janela consultada. A prévia local usa capturas desses agregados, identificadas como snapshot, sem atualizar os provedores automaticamente. Os cards de gestão e a atividade da prévia continuam fictícios.

Referências: [Render Metrics](https://render.com/docs/service-metrics), [OpenAPI Render](https://api-docs.render.com/openapi/render-public-api-1.json), [Supabase observabilidade](https://supabase.com/docs/guides/observability/metrics), [tamanho do banco](https://supabase.com/docs/guides/platform/database-size).
