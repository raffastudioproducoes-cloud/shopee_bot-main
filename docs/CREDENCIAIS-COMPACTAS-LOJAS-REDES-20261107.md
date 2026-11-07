# Credenciais compactas — lojas e redes sociais (homologação `staging`)

**Data:** 07/11/2026 · **Estado:** implementado localmente, aguardando CI/deploy de `staging` e QA autenticado. **SemVer:** melhoria de interface compatível, candidata MINOR ao próximo release (`VERSION=3.4.0` permanece até promoção autorizada).

## Requisitos e decisões

- Página `/credentials` ganha **duas abas**: **Lojas** e **Redes sociais**. Cada aba preserva os grupos **Já credenciados** e **Ainda não cadastrados**, ambos em ordem alfabética PT-BR e com contadores independentes.
- Cards escuros e compactos: ao fechar, exibir **logomarca transparente autêntica, nome e status à direita**, além de acionador acessível de expansão. Por padrão, iniciar fechados. Quando abertos, mostrar explicação com **segundo controle de expandir/recolher**, depois entrada/ação de conexão.
- Os textos, links, estados de erro, status de atualização, ações de desconectar e dados já existentes continuam acessíveis. Cabeçalhos conectados usam apenas estado curto; data e resultado do último teste ficam dentro do card aberto. Testes manuais de conexão deixam de aparecer para **qualquer papel** em `/credentials` e aparecem no painel administrativo `Resultado das conexões` somente para ADMIN. Credenciais de IA e API Shopee seguem no painel administrativo, sem exposição de chave a USER.
- **Lojas:** Shopee (ID de afiliado funcional); Shopee Vídeo (integração bloqueada e identificada); futuras Amazon, Americanas, AliExpress, Awin, Lomadee, Magazine Luiza, Mercado Livre, Natura e Avon, Pró Spin, Rakuten, SHEIN e TerabyteShop. Cadastros futuros são **informativos, sem formulário ou conexão fictícia**.
- **Redes:** Facebook, Instagram, Threads, TikTok e X preservam OAuth existente; Kwai preserva bloqueio; Telegram e WhatsApp entram como **Em breve**, sem inventar OAuth/WhatsApp Business API ou QR Code que não exista.
- A página traz instrução inicial sobre diferença entre **loja (identidade de afiliado)** e **rede (permissão de publicar)**, necessidade de conectar só os serviços usados e proteção dos segredos.
- Logomarcas reais SVG/PNG transparentes **salvas localmente**, com URLs individuais e notas de marca em [`frontend/public/brand-logos/SOURCES.md`](../frontend/public/brand-logos/SOURCES.md). Nenhum ícone precisa de CDN em tempo de execução. Marcas são propriedade de seus titulares; exibição identificadora não implica afiliação oficial.
- Nenhuma API de loja futura será acionada; sem migration, alteração em cron, `pg_net`, scheduler, postagens ou pagamentos. `main` só mediante aprovação posterior de Rafa.

## Aceitação

1. Dois separadores acessíveis alternam a lista sem perder estado, e `registered/pending` continuam isolados e ordenados dentro da aba.
2. Cabeçalho fechado compacto mostra logo, nome e status; acionamento por teclado, touch e mouse.
3. Ajuda pode ser aberta/recolhida **independentemente** do card; botão de conexão/salvamento existente mantém chamada real.
4. USER não vê `Testar conexão`; ADMIN não perde meios de diagnóstico existentes no sistema.
5. Integrações futuras não armazenam credenciais, não simulam status conectado, e têm status explícito **Em breve**.
6. Layout verifica 1440px e largura móvel, sem clipping de nome/status ou dupla linha desnecessária.
7. Testes selecionados de frontend/credenciais e build passam, com CI GitHub e Render staging LIVE antes de declarar implantação.

## Implementação e evidências

- Fonte: `frontend/src/pages/CredentialsPage.tsx` e `frontend/src/lib/credentialPlatforms.ts`; CSS: `frontend/src/index.css`; teste ADMIN: `frontend/src/pages/AdminCredentialsPage.tsx`; teste novo: `frontend/tests/credentials-compact-platforms.test.mjs` incluído na workflow CI.
- Nenhuma migração, alteração no Supabase/pg_cron, integração OAuth, API de publicação, plataforma IA ou receita de afiliados.
- Card futuro **não tem botão ativo de salvar ou conexão**. Não prometer que o link de afiliado dessas lojas funcione; habilitar individualmente conforme aprovação da API e implementação validada.
- **Pré-merge:** build Vite/TypeScript e 19 testes de frontend selecionados verdes (07/11). `pytest` focal de CSP não inicia localmente porque o fixture exige PostgreSQL não disponível no ambiente; verificação Node da igualdade das 380 classes CSP estáticas passou. CI fará o teste real em PostgreSQL isolado.
- **Pendência de QA visual:** verificar navegação autenticada em desktop/mobile após deploy na staging, com conta real e consentimento apenas se Rafa solicitar; não se fez OAuth nem publicação como teste.
- **Branch:** `feat/credenciais-compactas-lojas-redes-20261107`. Acrescentar PR, CI, SHA, Render LIVE e estado depois dos gates.
