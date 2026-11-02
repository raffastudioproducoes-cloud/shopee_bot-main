# Auto Orbital — Especificação vinculante: Criar POST, galeria Shopee e campanhas por lista

**Data:** 2026-11-02  
**Projeto:** Shopee Auto Orbital  
**Base canônica verificada:** `VERSION=3.0.0` em `main` e `staging`  
**Status:** requisitos de produto aprovados pelo proprietário; execução inicial em branch derivada de `staging`; nenhuma promoção automática para `main`.

## 1. Objetivo e regras de mudança

Restaurar e aprimorar o fluxo de publicação de listas anterior à migração tecnológica: buscar produtos Shopee, organizar lista, preparar um post independente por produto, editar conteúdo e mídias por item, selecionar redes sociais e programar campanha sequencial. Reorganizar o criador atual em página dedicada e permitir múltiplas imagens de origem Shopee também na postagem única.

**Escopo é vinculante.** Cada requisito deste documento precisa de tarefa, teste e registro no `CHANGELOG.md`. Se aparecer ambiguidade impeditiva ou limitação externa, documentar e pedir decisão: não descartar requisito nem mudar a regra silenciosamente. Usar `VERSION` como única fonte da versão atual; implementar primeiro em `staging`, promover somente após QA e aprovação do Rafa. A landing e animações estão fora deste escopo.

## 2. Regras funcionais fechadas

- **R01 — Navegação.** Na rota `/posts`, retirar o botão de criação e manter a lista/histórico dos posts e o modal de visualização. Adicionar item lateral `Criar POST` exatamente acima de `Automação` na navegação desktop e mobile; abrir página dedicada `/posts/criar`. Editar post existente pela mesma experiência dedicada em rota de edição, mantendo o `posts.id` original.
- **R02 — Continuidade.** Migrar todo conteúdo/funcionamento do modal de criação para página responsiva: redes, seleção de produto, lista, fotos Shopee, arquivos locais, persona IA, textos/variantes, partes de thread, compatibilidade, preview, `Agora`, `Recorrente`, agenda 24h Brasília, rascunhos e mensagens. Não regredir publicação única.
- **R03 — Modalidades.** Página `Criar POST` com `Publicação única` e `Campanha por lista`. Cada post enviado contém **um** produto; campanha não converte vários produtos em um único post.
- **R04 — Campanha.** Selecionar lista existente do perfil, criar cópia editável (snapshot) e definir ordem dos itens. Em cada item editar título/copy, link de afiliado, mídias, capa e versões de texto específicas das redes; permitir IA individual e preparação em lote com revisão humana. Editar campanha não altera a lista-fonte nem outras campanhas.
- **R05 — Redes.** Seleção global de redes compatíveis, igual à postagem atual. Manter validações reais por rede para texto, hashtags, links, mídia, vídeos/carrosséis, credenciais e restrições de publicadores; redes indisponíveis permanecem bloqueadas. Uma falha de rede não cancela as redes bem-sucedidas.
- **R06 — Galeria Shopee.** Permitir **mais de uma imagem** da Shopee por produto na postagem única e campanha, com miniaturas, seleção, reordenação, capa e adição de arquivos locais. O código atual só persiste `products.image`/consulta `imageUrl`: fazer levantamento da fonte **autorizada** de imagens adicionais antes de prometer captura automática. Se a API disponível não fornecer a galeria, registrar bloqueio técnico e manter alternativa de upload manual, sem scraping indevido. Preservar compatibilidade com a imagem única antiga; armazenar cópias seguras no Storage privado.
- **R07 — Compatibilidade de mídia.** Usar a infraestrutura `networkLimits`, `mediaAdapt`, `mediaComposition` e backend como autoridade final; escolher apenas mídia que cada rede/publicador entrega de fato. Avisar claramente quando algumas mídias não serão utilizadas, quando o post será só texto e quando determinada rede não poderá ser enviada. Aplicar a imagens e vídeos.
- **R08 — Janela e intervalo.** Campanha exige data inicial e data final inclusivas, máximo **30 dias corridos de calendário**, contando primeiro e último dia (`end_date - start_date <= 29` dias). Escolher dias da semana, hora inicial, hora final, intervalo entre posts e redes. Apresentar todos os horários válidos em fuso `America/Sao_Paulo` antes da ativação. Gerar horários apenas dentro da janela e do intervalo; hora final é inclusiva quando coincide com a grade.
- **R09 — Segurança anti-spam.** Intervalos, taxa por conta/rede, janelas e volume devem respeitar **restrições oficiais e capacidades realmente implementadas** de cada plataforma; validar no backend antes de ativar; exibir ajuste mínimo/sugestão e nunca deslocar publicação silenciosamente para fora da janela aprovada. Atualizar limites mediante documentação oficial; tratar 429/rate limits e bloqueios com segurança. Não prometer imunidade a banimento.
- **R10 — Rotação.** Cada slot da campanha aponta para **um item** da lista. Se horários > produtos, recomeçar do primeiro, mantendo ordem, até o último slot. Se produtos > horários totais dentro do período, alertar número exato de itens sem cobertura e oferecer ampliação de período/janela ou redução do intervalo; não ativar silenciosamente sem cobertura. Uma lista de N produtos e M slots usa `item_position = slot_sequence % N`.
- **R11 — Falhas.** Falha de um produto, horário ou rede **não interrompe a sequência**: próximo slot mantém sua posição original. Exibir estado por ocorrência (programado, executando, postado, erro, parcial, sem confirmação), com última postagem confirmada real. O usuário vê mensagem simples com produto/horário/rede; ADMIN recebe diagnóstico técnico. Sem retry automático de estado externo incerto.
- **R12 — Edição.** Uma campanha ativa pode ser editada **somente nas ocorrências futuras que ainda não entraram em execução**. Publicações finalizadas, falhadas ou com confirmação incerta preservam snapshot e auditoria; alteração no conteúdo-fonte não reescreve histórico. Pausa/retomada/cancelamento só afetam o futuro; replanejamento exige prévia e confirmação.
- **R13 — Identidade.** Preservar `posts.id` SERIAL global único e crescente (não reiniciar após exclusões), `#ID` em /posts e visualização. Identificar campanha e ocorrência separadamente; garantir independência para diferentes usuários, mesmo usuário, horário idêntico, produto repetido e redes distintas.
- **R14 — Rascunhos.** Recuperar estado do criador e da campanha após atualização/queda da internet; limpeza intencional deve continuar limpa. Nunca guardar tokens ou conteúdo binário de `File` no localStorage. Rascunhos de mídia persistidos com autorização/expiração e limpeza segura, conforme infraestrutura existente.
- **R15 — Multiambiente.** `staging` é **exclusivo de Rafa (dono/desenvolvedor)**, não utilizado por clientes finais; `main` é produção; compartilham o mesmo Supabase e o trabalho aprovado em staging é promovido para main. O cron Supabase desperta a produção e **não precisa duplicar disparo em staging**. O código/documentação atuais mostram scheduler e jobstore segregados por environment; investigar e reconciliar para agendas criadas em staging poderem ser consumidas corretamente pelo executor central, sem assumir que o pequeno número de usuários elimina corrida entre processos. Não duplicar publicações nem modificar horários legados sem migração compatível/auditoria.
- **R16 — Período por plano futuro.** **Nesta entrega todos podem usar até 30 dias**, sem diferenciação por assinatura. Fica como requisito FUTURO configurar duração e limites de criação/quantidade por plano usando tags/entitlements administráveis. Exemplos fornecidos: `Free 3 dias`, `Premium 15 dias`, `Premium 30 dias`; a duplicação do nome Premium é intencionalmente mantida como **exemplo ainda não definido**, sem presumir que se trate de Pro. Precificação/tags/quotas serão decididas em fase própria, não agora.
- **R17 — TikTok foto.** **PENDÊNCIA EXPRESSA DE ALTA PRIORIDADE pós-entrega:** revisitar fluxo de publicação de imagens/fotopost TikTok, requisitos de Creator Info, permissões/consentimento, conteúdo comercial, URL verificada e aprovação; não anunciar suporte que ainda não está implementado. Registrar para retomada assim que viável.
- **R18 — Documentação/QA.** Registrar cada alteração e falha/correção no `CHANGELOG.md`, atualizar documentação técnica/contratos e evidências de testes, distinguir `código`/`CI`/`staging live`/`publicação real`, manter conta de testes Shopee sem interferência. Não testar postagem externa sem destino e autorização explícita.

## 3. Arquitetura escolhida (delegação do proprietário)

**Escolhida: reutilizar o motor existente de `posts`, `publish_jobs`, mídias e idempotência; criar domínio de campanhas separado.** Alternativas rejeitadas: armazenar a lista inteira como um post (quebra a regra de um produto e oculta falhas por item); criar um segundo publicador independente/um executor por ambiente (duplica risco e regras).

Entidades sugeridas, sujeitas ao naming da base após inspeção:
- `publication_campaigns`: proprietário, perfil, lista de origem, nome, datas/horas/dias/intervalo/timezone/redes, estado e versão.
- `publication_campaign_items`: ordem, produto da conta, snapshot de título/link/textos por rede e referências de mídia/capa.
- `publication_campaign_occurrences`: instante UTC e instante local, índice sequencial, item associado, estado, ligação aos posts e prova/auditoria.
- `product_media_assets` ou similar: galeria ordenada por produto e fonte, com legado `products.image` preservado.
- `posts` e `publish_jobs`: permanecem livro-razão de publicação concreta, vinculados às ocorrências e com `#ID`.

Ativação e execução precisam ser atômicas/idempotentes por `campaign_id + occurrence_sequence + network`, com isolamento por `user_id/profile_id`, travas/claims transacionais, chaves únicas e acesso controlado/RLS. Evitar agendar infinitos jobs APScheduler; campanhas de até 30 dias permitem materialização limitada ou horizonte móvel com contrato de recuperação. Nunca reenviar em caso de resultado externo `unknown` sem reconciliação. Não usar filesystem efêmero do Render para mídia.

Estados de campanha: `draft`, `ready`, `active`, `paused`, `completed`, `cancelled`. Só instâncias futuras e ainda não reivindicadas podem ser editadas. Ao desativar/cancelar não apagar histórico; reativação é idempotente.

## 4. Experiência de usuário — Product Design

- `/posts`: histórico limpo, busca, filtro, resumo de campanha de origem, `#ID`, status e modal de detalhes; sem formulário de criação.
- `/posts/criar`: página dedicada com escolha de modalidade; preservar linguagem visual/tokens Auto Orbital. Edição em página, não modal longo e rolável. Desktop com hierarquia clara; Android com controles tocáveis.
- `Campanha`: selecionar lista → editor de produtos em ordem → redes/cópias por produto → mídias → período/intervalo → calendário de prévia/cobertura → confirmar/ativar.
- Mostrar em cada item: nome/foto/copy editável/CTA link/indicador de preparo/avisos por rede; evitar ruído visual de validações duplicadas.
- Mostrar no resumo: quantidade de produtos, datas, slots, número de ciclos, itens sem cobertura, restrições anti-spam e redes indisponíveis.
- O usuário deve conseguir retornar à edição sem perder rascunho; exclusão deliberada deve persistir.

## 5. Casos de aceitação obrigatórios

1. `5 produtos × 5 horários`: cada produto uma vez, um item por ocorrência.
2. `5 × 10`: rotação `1,2,3,4,5,1,2,3,4,5`.
3. `10 × 5`: alerta de exatamente 5 itens sem cobertura e nenhuma ativação silenciosa.
4. Campanha 30 dias inclusivos aceita; 31 dias rejeita; fevereiro e virada de mês corretamente calculados.
5. Hora final inclusiva quando encaixa; intervalos não encaixados não criam horário fora da janela.
6. Staging cria/edita campanha e produção executa uma vez; dois executores simultâneos não criam duplicações.
7. Dois usuários e dois perfis, segundo idêntico, nunca compartilham conteúdo, credenciais ou ID de ocorrência.
8. Um usuário, dois posts no mesmo segundo, com produto repetido, obtém dois `posts.id` distintos.
9. Falha em Threads no slot 3 não bloqueia slot 4 e não repete slots anteriores.
10. Rede incompatível com 4 imagens recebe subconjunto suportado, texto apenas com aviso ou bloqueio por rede; nunca falsa confirmação.
11. Edição de item futuro tem efeito nas futuras ocorrências, mas não nas já publicadas ou `unknown`.
12. Pause/resume preserva sequência, sem compensar silenciosamente horários passados; replanejamento precisa confirmação.
13. Rascunho recupera texto apagado intencionalmente; arquivos locais não são fingidos como recuperados.
14. Layout responsivo de página e menu, foco/teclado/Android, sem quebrar modal de detalhes de /posts.
15. `RafaelTesteCliente` permanece apta para homologação Shopee.
16. Limites anti-spam (intervalo mínimo, cota/janela, múltiplas redes e HTTP 429) geram aviso/recusa segura antes de disparo indevido.
17. Importar várias fotos somente de fonte validada, limites de tamanho, MIME, SSRF, Storage privado, autorização por usuário/perfil.
18. Rotinas antigas `Agora` e `Recorrente` mantêm os resultados anteriores e não perdem IDs.

## 6. Sequência de entregas e SemVer

- **F0 / `3.0.1` PATCH (se reproduzida incompatibilidade):** auditoria e correção de execução de agendas entre staging e produção, sem quebrar a regra de negócios ou disparar posts teste reais.
- **F1–F2 / `3.1.0` MINOR:** página exclusiva `Criar POST`, navegação e galeria de múltiplas imagens; só promover quando a origem/licitude da galeria estiver resolvida e as mídias testadas.
- **F3–F5 / `3.2.0` MINOR:** editor de campanhas por lista, preparação individual, 30 dias, slots inteligentes, rotação, execução, recuperação, estados e monitoramento.
- **F6 / `3.2.1` PATCH somente se houver bug:** estabilização; nunca antecipar bump no `VERSION`. Em staging registrar no `CHANGELOG.md` seção `[Não lançado]`, atualizar `VERSION` na promoção aprovada.
- **Posterior, SEM implementar agora:** tags de planos/limites comerciais/quantidades e suporte de imagens TikTok.

## 7. Observações verificadas no repositório em 2026-11-02

- `frontend/src/pages/PostsPage.tsx` mistura histórico e formulário, `PostModal` contém estados de IA/mídias/horários e rascunho.
- `frontend/src/pages/PanelPage.tsx` organiza itens do menu; `frontend/src/router.tsx` expõe `/posts` e `/automacao-posts`.
- `frontend/src/lib/mediaAdapt.ts`, `frontend/src/lib/networkLimits.ts` e `api/network_limits.py` fazem adaptação por capacidade do publicador; preservar lógica/testes.
- `apis/shopee.py` e `api/routers/catalog.py` consomem `imageUrl` singular; `api/routers/posts.py` importa uma foto de produto validando host/MIME/tamanho. A galeria exige nova fonte de dados.
- `docs/SCHEDULER-ENVIRONMENTS-20261102.md` descreve jobstores segregados e staging ligado, conflitando com a decisão posterior de execução central de produção. Fazer correção compatível e documentar o estado efetivo.
- Supabase é compartilhado; não efetuar migração destrutiva, não alterar tokens nem endpoints sem testes.

## 8. Riscos, pendências e proibições

**Riscos a resolver antes de concluir:** disponibilidade legal/técnica das fotos adicionais da Shopee; limites oficiais por rede e capacidade do publicador; consumo de Storage/IA; idempotência na transição staging→produção; revisão de mídia/credenciais/conta teste.

**Pendente de pós-entrega:** TikTok Photo Direct Post (`R17`); entitlements/tags e durações comerciais por plano (`R16`); precificação e cotas; possíveis campanhas sem data final (não aprovadas para esta entrega).

**Não fazer:** remover funcionalidades atuais de post único; desbloquear redes não suportadas; inferir êxito de postagem pelo agendamento; reenviar automaticamente `unknown`; configurar duplicidade cron em staging; alterar `main` sem aprovação; salvar segredos localmente; eliminar linhas antigas compartilhadas; ampliar escopo para landing/animações.

## 9. Critério de saída

Código e testes de cada fase concluídos em branch derivada de staging; CI verde; staging live verificado com conta e dados autorizados; documentação atualizada com evidências e pendências; aprovação estética/funcional de Rafa antes da promoção de cada versão para `main`. Sem evidência real, status `não validado E2E` deve ser explícito.
