# Auto Orbital — F4: Planos, permissões e cotas (decisão de Rafa)
**Decisão de produto:** 03/11/2026. **Status:** regras confirmadas documentadas; execução progressiva em staging. Não é prova de cobrança ou de publicação real.

## 1. Fonte, precedência e isolamento
- Planos comerciais: **Free, Pro e Premium**. `Plus` é rótulo legado a migrar de forma compatível, jamais quarto plano comercial. A base atual usa `profiles.plan_tier` com check `free|plus|premium`; em 03/11 todos os três perfis existentes estavam `free` antes da alteração pontual da conta de teste. `users.access` guarda **USER/ADMIN** separadamente.
- **ADMIN** (papel comprovado no backend) não sofre cotas nem bloqueios comerciais, independentemente de um rótulo legado `free`. Isso **não** contorna autorização, privacidade, segurança, limitação oficial da rede, capacidade física nem proibições de redes externas.
- Conta pode ter um perfil principal + até dois secundários (**três perfis**, limite estrutural vigente). Free não pode criar secundários; Pro/Premium podem chegar a três. Eventual exceção do teto estrutural para ADMIN precisa implementação e compatibilização do trigger SQL; não alegar pronta.
- **Compartilhados pela conta:** catálogo de produtos, credencial Shopee, configuração/IA. **Isolados por perfil:** listas, redes/OAuth, posts, agendamentos, mídias de publicação, preferências. Portanto, a quantidade de **produtos é por conta**, e cotas de listas e publicações são **por perfil**; uma mesma assinatura Pro/Premium habilita os perfis daquela conta. Não duplicar catálogo nem segredos entre perfis.
- O cliente não decide o plano, a cota ou se é ADMIN. Toda autorização e consumo devem ser validados no backend, protegidos contra concorrência e abuso. Compatibilizar staging/main, que compartilham Supabase.

## 2. Matriz aprovada e lacunas explícitas

| Recurso | Free | Pro | Premium | ADMIN |
|---|---|---|---|---|
| Produtos salvos (catálogo por conta) | 100 | 500 | **2.000** | Sem cota comercial |
| Listas (por perfil) | 20 | 20 | **100** | Sem cota comercial |
| Enviar agora | 1 postagem/h | 3 postagens/h | **5 postagens/h** | Sem cota comercial |
| Recorrente | Seleção de até 7 dias da semana; 1 postagem/dia | Até 7 dias; até 5 horários de postagem disponíveis por dia | **Até 5 horários/dia** | Sem cota comercial |
| Campanhas | **Sem acesso** | Até 15 dias; até 3 postagens/dia; **2 campanhas ativas/perfil** | Até 30 dias; 1–15 postagens/dia; **5 campanhas ativas/perfil** | Sem cota comercial |
| Criar perfil secundário | Bloqueado | Permitido, até 3 perfis no total | Permitido, até 3 perfis no total | Acesso irrestrito por plano; teto estrutural a tratar |
| Automação | Vitrine bloqueada e chamada para upgrade | Vitrine bloqueada e chamada para upgrade | Permitida | Permitida |
| Dashboard, Análises, Credenciais, Perfis (visualização), Configurações, Ajuda e FAQ | Disponíveis | Disponíveis | Disponíveis | Disponíveis |

- A duração absoluta de qualquer campanha é no máximo **30 dias**, incluídos início e fim. A opção de quantidade diária do compositor já vai de 1 a 15; ao ativar, o backend aplicará também o teto de **3** para Pro.
- Recurso não incluído no plano permanece visível como **bloqueado**, com explicação e CTA de upgrade. Não ocultar controles de segurança nem induzir usuário a pensar que o pagamento habilita APIs externas sem aprovação.
- Os limites comerciais devem ser **editáveis pelo administrador futuramente** sem alterar código: tabela de política versionada e auditável, leitura no servidor e invalidação de cache. Não inventar preços, cobrança ou checkout.
- **Decisão adicional (03/11/2026, substitui Pro=0 anterior):** Pro = **2** campanhas simultaneamente ativas por perfil; Premium = **5**. Cada publicação por rede consome **1 unidade** do limite de postagem (um envio para três redes = três unidades). Cotas diárias de campanha e horários recorrentes são categorias distintas; a contagem dos posts não se confunde com número de jobs/partes de thread.
- **A confirmar separadamente:** exceção do teto físico de 3 perfis ADMIN e regras de contratação/preço. Sem necessidade de nova confirmação para os tetos comerciais acima.
- As políticas de uso próprias de Threads, Instagram, Facebook, TikTok etc. impõem limites adicionais. O produto deve ajustar a frequência por rede e evitar spam; a cota do plano nunca autoriza violar a plataforma.

## 3. Fases de implementação, sem afetar outros módulos
1. **F4A — Inventário, identidade e rótulos [INICIADA]:** conferir schema e código; documentar matriz; reconhecer `plus` como legado de `Pro` na apresentação, preservar compatibilidade da produção. Conta `RafaelTesteCliente` (USER de suporte, com perfil principal) foi alterada pontualmente de `free` para `premium` em `profiles.plan_tier`, com leitura posterior confirmando; `rafastudio` continua `ADMIN`, embora o badge legado do perfil ainda registre `free`. Esta operação **não concedeu privilégios administrativos nem mudou os jobs**.
2. **F4B — Política central + DB:** definir fonte única de plano por conta e catálogos de limites editáveis; migração SQL aditiva, RLS/grants, compatibilidade `plus`, auditoria de mudanças e atualização coerente dos perfis da conta. Backend ADMIN bypass em todas as rotas comerciais. Antes de deploy, aplicar e registrar migration sem dupla execução. Testar fallback, downgrade, ownership, travas e concorrência.
3. **F4C — Guardas de quota:** enforce atômico nos endpoints de criar/importar/restaurar produtos, criar/importar listas, criar/disparar posts “agora”, recorrência, perfis e campanhas; contagens por conta/perfil corretas. Exclusão e redução de quota não apagam registros antigos; mostrar uso/limite e erro localizado. Para operações com muitas redes, contar somente segundo regra comercial decidida.
4. **F4D — Interface de acesso:** etiquetas Free/Pro/Premium, destaque de ADMIN, status de consumo e estados bloqueados com upgrade no design system responsivo PT-BR. Automação exclusivamente Premium/ADMIN com vitrine visível para outros. Módulos comuns continuam utilizáveis; nenhuma tela “trancada” só por ser ADMIN.
5. **F4E — Ativação controlada de campanha:** só após cotas e segurança persistidas; validar plano, janela, dias, redes, mídia, permissão e crédito de execução; criação transacional/idempotente de jobs; congelamento de edição em T−30 min e imutabilidade de post publicado; rejeitar conflito/duplicata; staging sem disparos reais de teste por padrão.
6. **F4F — Painel administrativo de políticas e homologação:** edição auditável dos números por plano, trilha de alterações, transição upgrade/downgrade, contratos/termos, testes focados com dois usuários/dois perfis, CI e Render staging, sem promoção à `main` até aceite de release.

## 4. Regras de entrega
- Verificar a aplicação em staging, registrar branch/PR/SHA/CI/deploy e evidência; promover `main` só com autorização própria. `VERSION=3.0.0` não muda antes de release.
- Supabase é compartilhado: nenhuma seed de cliente, postagem real ou migração destrutiva. Fazer mudanças idempotentes e compatíveis com a versão antiga de produção.
- Preservar upload local/Shopee, Storage privado, RLS, OAuth, limitações de cada rede, isolamento e arquitetura de jobs existentes. Não criar quota de imagens acumuladas por perfil.
- **Não confundir documentação com enforcement**: cada linha só ganha marca de concluída após código, teste e deploy evidenciados.

## 5. Entrega incremental F4B — política central e quotas atômicas de catálogo/listas (03/11/2026)
- Migração proposta: `072_plan_limits_and_atomic_catalog_quotas.sql` adiciona `users.plan_tier` (fonte por conta, compatível com `plus`), `plan_limits` editável, auditoria de alteração da política e duas RPCs de inserção atômica. O backfill da conta é executado **somente na primeira criação da coluna**: posteriores downgrades não são revertidos.
- API staging: criação de produto (catálogo compartilhado) e lista (perfil ativo) passam pelas RPCs; lock transacional na linha de `users` evita contagens concorrentes excedendo o teto. Erros de cota são traduzidos em HTTP 409. API anterior de produção continua com INSERT tradicional: **nenhum trigger global de cota de catálogo/lista**, já que Supabase é compartilhado. ADMIN comprovado pelo campo `users.access` ignora teto comercial nas duas RPCs.
- Tabelas internas `plan_limits` e `plan_limits_audit` têm RLS habilitada; `anon`/`authenticated` não recebem permissão; RPCs executáveis apenas por `service_role`. Credenciais não saem do backend. Auditoria registra valor anterior e novo, sem alterar preço/checkout.
- **F4C ainda pendente** após F4B: enforcement de quotas de perfis, envios imediatos por rede/hora, agendas recorrentes, campanhas ativas e automação. O rascunho de campanha não é campanha ativa. Nem DB compartilhado nem produção podem receber trigger global antecipado; definir execução idempotente com reserva transacional ao ativar/agendar.
- Evidência de PR, CI e implantação será anexada após a entrega; não classificar F4B como homologada antes disso.
