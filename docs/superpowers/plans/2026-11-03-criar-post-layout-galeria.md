# Criar POST — Layout Responsivo e Galeria Shopee: Plano de Implementação

> **Para execução assistida:** usar `superpowers:executing-plans` em linha, limitando testes aos controles afetados.

**Objetivo:** concluir o experimento de galeria extra e transformar o compositor de criação em uma página visualmente integrada ao Auto Orbital.  
**Arquitetura:** a rota atual `/posts/criar` mantém o estado e contrato de envio; apresentação segregada pela classe `.is-create-mode` e novo CSS isolado. Não modificar o editor de revisão nem endpoints.  
**Stack:** React/TypeScript, CSS com tokens existentes, GitHub Actions, Render staging.  
**Especificação:** `docs/superpowers/specs/2026-11-02-campanhas-listas-design.md` (R01, R02, R06, com decisão de indisponibilidade da galeria).  

## Restrições globais

- Alterações limitadas a `staging`; `main` e PR #198 DRAFT preservados.
- Foto principal Shopee e upload local de fotos/vídeos mantidos.
- Nenhum post real, upload de teste, mudança de backend/cron/Supabase.
- T−30 e revisões futuras de posts existentes inalteradas.
- Registros no `CHANGELOG.md`, documento técnico e Vault.

## Focos de revisão

- Mobile 360–390px sem overflow horizontal ou modal visual.
- Tablet: preview sem `position: fixed` e sem backdrop.
- Desktop: editor usa largura útil e agrupa produto/mídia e texto/agendamento.
- Fluxo de criação preserva payload `createBatch` e seleção única de produto.
- Edição de post existente preserva modo anterior.

### Tarefa 1 — Encerrar galeria experimental (pesquisa, decisão)

**Arquivos:** `docs/CRIAR-POST-LAYOUT-GALERIA-SHOPEE-20261103.md`, `CHANGELOG.md`; cópia informativa dentro da ajuda da foto principal no `PostComposer.tsx`.

- [x] Verificar 3 sondagens anteriores do endpoint autenticado `productOfferV2`.
- [x] Abrir link original real de produto cadastrado, documentando a tela recebida.
- [x] Registrar decisão: sem galeria extra confiável sob a fonte atual; preservar foto principal e upload manual.
- [ ] Confirmar após deploy que checkbox Shopee e upload continuam visíveis.

### Tarefa 2 — Layout de página no compositor

**Arquivos:** `frontend/src/pages/CreatePostPage.tsx`, `frontend/src/components/posts/PostComposer.tsx`, `frontend/src/components/posts/postComposerPage.css`.

- [x] Remover do modo criação o contêiner de modal centralizado; alinhar cabeçalho aos tokens existentes.
- [x] Estruturar regiões e colunas responsivas sem alterar estado ou submit.
- [x] Converter prévia da criação em região inline nas telas menores; manter editor de post existente.
- [ ] Rodar pipeline TypeScript/build/testes CI e corrigir regressões apenas se detectadas.
- [ ] Inspeção curta da rota em desktop/mobile no staging após deploy.
- [ ] Registrar resultado no Vault e entregar continuação da campanha por lista.

## Decisão de abordagem

Ajuste incremental no design system existente, sem introduzir novo framework, componente modal ou serviço de imagem. Alternativas descartadas: reescrever formulário inteiro (alto risco de regressão), importar imagens da página pública sem contrato autorizado (risco de acesso e instabilidade), ou deixar seletor experimental indefinido.
