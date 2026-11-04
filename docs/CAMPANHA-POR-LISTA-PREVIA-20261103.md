# Auto Orbital — Campanha por lista: prévia isolada (2026-11-03)

## Estado e escopo
- Entrega experimental em **staging**, PR #204, sem alteração de produção ou Supabase.
- Nova escolha em `/posts/criar`: **Publicação única** (fluxo anterior preservado) / **Campanha por lista**.
- A campanha **não é ativável** nesta entrega. O botão **Calcular prévia** só consulta `POST /campaigns/preview`.
- A API tem autenticação por usuário/perfil e somente `SELECT` das listas/produtos, sem qualquer `INSERT`, `UPDATE`, `DELETE`, job, agendamento ou publicação.

## Funcionalidade implementada
1. Selecionar uma lista existente do perfil ativo (até 100 listas mostradas).
2. Montar a ordem dos produtos, com botões subir/descer; a sequência é um **snapshot de IDs no rascunho local**, não edita a lista original.
3. Escolher datas inicial/final (máximo absoluto de **30 dias corridos inclusivos**), dias da semana, janela diária e intervalo em minutos.
4. O serviço gera uma ocorrência por horário e associa **um produto por ocorrência**, recomeçando a sequência quando todos foram usados.
5. Prévia local no fuso `America/Sao_Paulo`, resposta com horário local e UTC, contagem, aviso de produtos sem primeiro horário e primeiros 60 slots (limite de 2.000 por consulta).
6. Rascunho salvo só no navegador, isolado pelo usuário/perfil, sem arquivos, tokens ou credenciais. Um item removido da lista invalida a prévia no servidor em vez de aceitar IDs arbitrários.
7. Layout responsivo feito com tokens do site: grid no desktop, uma coluna nas larguras menores, sem modal nem popup.

## Fronteiras de segurança e decisões existentes
- **Não executa disparo**, cron, publicações ou criação de registros de campanha.
- Sem tocar no fluxo `PostComposer` da **Publicação única**, suas fotos da Shopee, upload do PC/celular, mídia ou agendamento existente.
- Futuro backend de ativação deverá aplicar cotas por plano, número máximo de criações, políticas de intervalo por rede, prova de consentimento e **T−30 min** (edição somente para posts não publicados e com mais de 30 minutos até disparo). Post publicado nunca é editável.
- Staging serve exclusivamente para o desenvolvedor; produção não foi alterada.
- Fluxo de imagens extras da Shopee encerrado em relatório anterior: API autenticada atual retorna imagem principal; extras automáticas não suportadas com a fonte validada. Upload manual continua.

## Validação proporcional
- Testes de lógica pura: prazo inclusive, 30/31 dias, dias/intervalo, revezamento, fuso, horário de verão.
- Testes do endpoint isolados: usuário/perfil, rejeição de produtos forjados/duplicados, UTC e `activated=false`.
- CI frontend TypeScript/build e suíte API; conferência visual em staging após deploy, quando possível.
- Nenhum disparo real ou dado de produção deve ser criado no teste.

## Próxima etapa (não habilitada)
Implementar persistência e ativação transacionais/atômicas no servidor, limites por plano e rede, prevenção de duplicações, media snapshots, revisão protegida T−30 e políticas específicas de postagem; somente após isso habilitar o botão de ativação. O fluxo TikTok de fotos segue anotado para revisão futura.
