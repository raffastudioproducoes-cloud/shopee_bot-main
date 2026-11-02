# Auto Orbital — Campanhas por listas: diário técnico da implementação

**Data:** 02/11/2026 (America/Sao_Paulo)  
**Baseline:** `VERSION = 3.0.0`; `main` e `staging` não foram alterados por estas mudanças.  
**Branch isolada:** `feat/campanhas-listas-20261102`  
**Revisão:** PR #198, rascunho, destino `staging` (nenhum merge/deploy).

> Este documento distingue deliberadamente implementação em código, testes automatizados, revisão em navegador, staging publicado e execução real de redes sociais. Um deles **não** substitui o outro.

## Escopo normativo e decisões de Rafa

Referência integral: [especificação](superpowers/specs/2026-11-02-campanhas-listas-design.md) e [plano de 15 tarefas](superpowers/plans/2026-11-02-campanhas-listas-implementacao.md).

- Staging é exclusivo de Rafa, desenvolvedor e proprietário; clientes finais utilizam a produção. Os serviços compartilham Supabase, e a produção já recebe o despertar do cron Supabase: não instalar um segundo cron de disparo no staging.
- Cada publicação tem seu próprio ID; cada ocorrência de campanha executa **um produto** no horário, mesmo que outra conta ou outro post esteja marcado para o mesmo segundo. Repetições/duplicidades técnicas não são autorizadas.
- Campanha tem data inicial e final, **máximo de 30 dias corridos inclusivos**. Cotas de duração/criação por plano e tags de entitlement ficam para a fase comercial; os exemplos de três, quinze e trinta dias não são restrições ativadas agora.
- Se os horários superarem os produtos, a lista recomeça; se os produtos superarem os horários, a UI deve emitir aviso de cobertura antes de ativar. Falhas não param a fila. Revisão de campanha ativa só altera futuras ocorrências ainda não reivindicadas; a sequência não recomeça.
- Ritmo e conteúdo obedecem às restrições documentadas de cada rede, sem prometer ausência absoluta de bloqueios. **TikTok Photo** está pendente de auditoria específica de alta prioridade.
- Publicação individual continua limitada a um produto; a nova campanha tem edições e snapshots independentes por item.

## F0 — Scheduler central: diagnóstico e contrato (parcial)

**Implementado na branch:**
- `database/scheduler_environment.py::publication_executor_environment()` responde autoridade `production` nos dois ambientes autorizados, sem confundir identidade da instância com quem publica; branch Render desconhecida falha fechada.
- Testes RED→GREEN do novo contrato em `tests/scheduler/test_central_dispatch_contract.py`. CI de contrato validada em [run #41504637098](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41504637098).

**Não implementado:** reconciliador durável entre intents criadas no staging e o executor de produção; migração segura de agendas antigas; desligamento consistente da publicação por worker de staging. A função de contrato **não corrige sozinha** o erro do agendamento. Diagnóstico completo: [F0](POSTS-CAMPANHAS-F0-SCHEDULER-DIAGNOSTICO-20261102.md).

**Bloqueio técnico:** main atual não reconhece um contrato novo de campanha antes de receber código compatível. A implantação de execução central precisará preservar posts antigos e ser faseada; não apontar dois APSchedulers para o mesmo SQLAlchemyJobStore.

## F1 — Criar POST como página (implementado em código; QA visual pendente)

- Nova rota privada `/posts/criar`, registrada dentro do layout autenticado em `frontend/src/router.tsx`.
- Nova entrada **Criar POST**, imediatamente acima de **Automação** no menu lateral (`PanelPage.tsx`).
- `PostsPage.tsx` deixa de ter o botão/modal de criação, mas mantém a listagem `#ID`, detalhes, publicação manual existente, conciliação e exclusão.
- `PostComposer.tsx` foi extraído como componente reutilizável sem `<Modal>`; continua usando um único seletor de produto, persona IA, variants de texto, seleção de redes, prévia, mídias, `Agora`/`Recorrente`, horários e `useAutosavedDraft`.
- `CreatePostPage.tsx` recebeu o mesmo fluxo de criação batch/adaptação por rede, upload privado, validação de scheduler antes de upload e tratamento de sucesso parcial, preservando o rascunho no caso de falha.
- Teste RED do novo contrato de página na [run #41507968517](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41507968517); testes existentes atualizados **para buscar o editor em seu novo arquivo**, mantendo suas asserções sobre segurança e mídias.

**Pendente:** abrir no navegador desktop/Android para avaliar foco, rolagem, visual e fluxo com conta de teste autorizada; tratamento real de `/posts/:id/editar` (se necessário para edição de post comum), e revisão de acessibilidade. Não chamar F1 de concluída em staging antes desses testes.

## F2 — Várias fotos Shopee (não iniciada)

O código atual de catálogo (`apis/shopee.py`, `api/routers/catalog.py`, `api/routers/products.py`) consome e persiste `imageUrl`/`image` singular; não há galeria multi-imagem verificada. A API de afiliados permite consulta de ofertas de produtos, mas a capacidade de retornar galerias ordenadas precisa ser comprovada em fonte/autorização oficial (sem scraping ou endpoint privado).

- Captura autorizada + modelo aditivo de galeria: pendente.
- Escolha/reordenação/capa de múltiplas fotos em **post individual e campanha**: pendente.
- Adaptação por rede com avisos de texto apenas ou mídia limitada: contrato atual a reutilizar, não declarado finalizado para galerias.

## F3 — Campanhas por lista (não iniciada)

Schema com owner/perfil/RLS, snapshots por item, editor com texto/link/fotos/reordenação, rascunho próprio e variantes por rede pendentes. Nenhuma migration foi aplicada ao Supabase compartilhado.

## F4 — Calendário e política de ritmo (parcial)

**Implementado na branch:** `api/campaign_schedule.py::plan_campaign_slots()`, módulo puro, sem DB/API externa, e `tests/api/test_campaign_schedule.py` com:
- um produto por slot; índice 0-based e rotação depois do último produto;
- janelas de data inclusivas (30 válidas / 31 rejeitadas), horário final alinhado inclusivo;
- datas/intervalos/dias inválidos e seleção sem coincidência;
- `America/Sao_Paulo` com conversão explícita para UTC;
- rejeição de hora local inexistente/ambígua por mudança histórica de fuso;
- parâmetro `start_occurrence_index` para retomada sem reiniciar o contador.

Teste RED por módulo ausente: [run #41505611995](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41505611995). Testes GREEN em conjunto com a suíte de API na [run #41508703774](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41508703774).

**Pendente:** calcular cobertura/alerta de produtos excedentes no frontend, bloquear ativação sem slots futuros, UI do calendário, políticas oficiais de intervalo/cota/429 por rede e validação autoritativa no servidor. O planejador **não** envia posts.

## F5 — Execução de campanha (não iniciada)

Pendentes: ledger imutável por ocorrência, idempotência, snapshot/revision, ativar/pausar/retomar/cancelar, processamento atômico por produto/rede, status simplificado USER e diagnóstico ADMIN, sincronização correta de última publicação e continuidade apesar de falha. Nenhum post externo foi enviado durante estes testes.

## F6 — QA, versões e promoção

**Verificação automatizada da branch — run #41508703774:**
- Frontend: testes de contrato da rota/editor e regressões de rascunho + TypeScript/Vite build **sucesso**.
- API: **1041 testes passaram**.
- Scheduler: **136 testes passaram**.
- Migrações/testes de segurança de índices: **4 passaram**.
- Proxy/CSP/bridge: **27 passaram**.
- Testes externos de staging: **pulados** (workflow reserva essa etapa à promoção `staging → main`).
- Testes de navegador, Android, conta `RafaelTesteCliente`, Supabase live/cron, campanha real e mídia Shopee multi-foto: **não executados**.

**Versionamento:** `VERSION` continua `3.0.0`. Mudanças permanecem em `CHANGELOG.md [Não lançado]`. Previsões: `3.0.1` se F0 for só correção de bug; `3.1.0` após página e mídia aprovadas; `3.2.0` após campanhas completas. Nenhum número de release foi publicado.

## Próximos checkpoints obrigatórios

1. Resolver F0 com contratos de criação/cancelamento em ambos ambientes, **sem** duplo executor e preservando jobs legados. Testar concorrência no banco e rollout compatível.
2. Confirmar fonte oficial da galeria Shopee; bloquear ou pedir decisão se não houver capacidade autorizada.
3. Concluir F1 com QA visual em staging autorizado; não antecipar merge.
4. Implementar F2→F5 com TDD, migration aditiva, isolamento de usuário/perfil e histórico; respeitar todo o escopo normativo.
5. Validar a conta teste Shopee, registrar evidências reais e submeter staging para aprovação do Rafa; só então preparar main.

**Risco residual principal:** os códigos de F1/F4 passaram em testes, mas a cadeia de criação no staging e execução central na produção **ainda não está implementada**. É incorreto anunciar campanhas prontas ou agendamentos convergentes.

## F0 — checkpoint adicional: regressões automatizadas (02/11/2026)

- Commit [`1b5cb3b`](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/commit/1b5cb3b13d77682b19e71f88740b292c94aee30d) acrescentou `tests/scheduler/test_central_dispatch_gap.py`, exclusivamente com simulações; não mexeu no runtime nem no banco.
- Três testes demonstram os filtros atuais por ambiente e o registro no scheduler local. Um quarto contrato de execução centralizada permanece `xfail(strict=True)`: é uma lacuna **esperada**, não uma correção já entregue.
- [CI #41527390056](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41527390056) concluído com verificações Python e frontend aprovadas; os jobs externos e a prévia Supabase foram pulados.
- Próximo gate: auditoria **somente leitura, com autorização aplicável**, das agendas de staging e jobs antigos antes de propor compatibilidade/migração; depois teste da solução com o fluxo `Agora`, recorrência, cancelamento, claims concorrentes e estados `unknown`. Nenhum teste E2E externo foi realizado.

## F0 — auditoria operacional do Supabase autorizada (02/11/2026)

- Executadas apenas consultas `SELECT` de esquema e agregados no projeto Supabase compartilhado, observação às **18h32 Brasília**; sem alterar jobs, dados, configuração, serviços, arquivos de usuário ou publicar externamente.
- Inventário: 11 agendas (6 produção, 5 staging); jobstores isolados 3/6 registros, respectivamente, contando 1 job de recuperação em cada; 4 registros `date` históricos da produção sem jobstore, todos com data passada e histórico de execução.
- Risco: `publish_jobs` mostra **8 `unknown`**, dos quais **6** têm indício de início de chamada externa. Proibido novo disparo automático ou migração que os reencaminhe.
- Cinco cron de staging são ativos e pertencem ao mesmo post/perfil. A migração depende de escolha explícita do Rafa quanto à preservação ou encerramento desses testes. Os detalhes, ressalvas e sequência de rollout estão em [F0 — diagnóstico](POSTS-CAMPANHAS-F0-SCHEDULER-DIAGNOSTICO-20261102.md).
- **Estado F0:** Task 1 de auditoria read-only concluída; Task 2 de convergência central pendente, sem migration nem deploy.

## F0 — implementação em branch, gate central desligado (02/11/2026)

- Opção 3 confirmada pelo Rafa: cinco agendamentos legacy do staging permanecem ativos, sem transferência nem exclusão. A auditoria read-only anteriormente registrada segue como fonte de contagens e estado dos `unknown`.
- Commits de implementação: [`93ab11c`](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/commit/93ab11cd21d9c8bc86a35553cfb00c8ba3f1d115) (gate + migration 068 preparada), [`8938abb`](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/commit/8938abb810881f4871154310a676cbb3edbcbb2a) (filtros de escopo), [`7e74cab`](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/commit/7e74caba2b845dd7ebc9ed8bfe11fca162602b05) (espelhamento central), [`cc674e3`](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/commit/cc674e307fb67671aa68fc429af4ef4281bd901a) (testes), seguidos das correções de compatibilidade [`8e88803`](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/commit/8e88803a25e300a30eda53037bd4ec8e5aa244c1), [`43a1320`](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/commit/43a1320a209cbab76f6f3b7f24891bdb7242497e) e [`34ddf11`](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/commit/34ddf11f6e8fb8a029b6f6e2f16f268601dc605a).
- CI inicial de integração [#41533071158](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41533071158): 3 falhas de contrato do INSERT legado (além de 161 testes do scheduler aprovados, 1 xfail esperado), corrigidas sem modificar as expectativas antigas. CI final [#41533585972](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41533585972): **sucesso** (API, testes Python, frontend), externo staging pulado.
- O mecanismo prepara a convergência de **agendas novas opt-in**; nenhuma agenda atual migrou e nenhuma publicação real foi executada neste trabalho. `ORBITAL_CENTRAL_DISPATCH_ENABLED` segue desligada por padrão. A migration 068 está no GitHub mas **não aplicada**; cuidado porque o boot executa migrations automaticamente após deploy.
- Pendências para completar F0: expiry observável para `date` perdida há mais de 1h; resposta de indisponibilidade e repetição segura de `Agora`; provas E2E reais com dois serviços/claims e homologação explicitamente autorizada. Ver [diagnóstico F0](POSTS-CAMPANHAS-F0-SCHEDULER-DIAGNOSTICO-20261102.md).
