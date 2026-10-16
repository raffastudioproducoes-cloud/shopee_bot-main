# Guia de Orquestração Multiagente — Economia Máxima de Tokens

> **Manual Operacional de Delegação e Execução**  
> **Agentes Cobertos:** Claude, Codex, Hermes e Antigravity  
> **Objetivo:** Orquestrar múltiplos agentes autônomos com custo mínimo de tokens, divisão estrita de papéis por modelo e isolamento total de branches e ambientes.  
> **Data:** 15 de outubro de 2026

---

## 1. Princípios Fundamentais de Economia

1. **O Claude é o Revisor e Orquestrador Central:** Não gaste a cota do Claude com tarefas mecânicas, varreduras pesadas de arquivos, pesquisa de mercado ou execução repetitiva de testes.
2. **Contexto Mínimo e Focado:** Subagentes não herdam contexto desnecessário. Cada tarefa enviada a um agente deve conter apenas o contexto estritamente necessário (caminhos exatos de arquivos, regras de ouro, comandos de teste e formato do retorno).
3. **Isolamento por Git Worktree:** Toda e qualquer tarefa de modificação de código deve rodar em um worktree próprio (`_tmp/wt-<nome>`), associado a uma branch `feat/<nome>` ou `fix/<nome>` a partir de `staging`.
4. **Dono da Coleta:** Quem delega é responsável por receber o resultado, verificar o `git diff`, validar os testes e reportar o estado consolidado. Nunca encerre um turno declarando que está "esperando" um subagente sem verificar os resultados.
5. **Parada Imediata ao Fim de Cota:** Se a cota de um agente esgotar, a execução é interrompida imediatamente. Nenhum agente deve continuar em loop ou aguardar em segundo plano sem solicitação explícita do usuário.

---

## 2. Pré-Voo: Verificação de Cota Obrigatória

Antes de iniciar qualquer fila de tarefas ou despachar jobs demorados, teste a disponibilidade de cota com comandos rápidos de baixo custo:

| Agente | Comando de Teste de Cota | Comportamento Esperado | Comportamento em Caso de Falha / Esgotamento |
|---|---|---|---|
| **Codex** | `codex exec "ping"` | Retorna confirmação rápida em poucos segundos | Exibe mensagem de erro `usage limit exceeded` ou recusa de requisição por cota |
| **Hermes** | `hermes -z "ok"` | Imprime `ok` e encerra com código 0 | Falha de autenticação, erro de timeout ou erro de runtime |
| **Claude** | Inspeção de uso no chat / limites de plano | Requisições normais no orquestrador | Alerta de rate limit ou limite de mensagens do ciclo atingido |
| **Antigravity** | Chamada leve de leitura ou teste local | Execução imediata sem erro de cota | Erro de rate limit ou quota da API Gemini |

> [!CRITICAL]
> **Sem cota, não despache.** Se um agente acusar limite de uso, **não insista**. Redirecione a tarefa para um agente com cota livre ou registre a pendência no relatório para retomada futura.

---

## 3. Matriz de Modelos por Tipo de Tarefa

Nunca desvie da atribuição de modelos abaixo. O roteamento incorreto (por exemplo, chamar modelos pagos do Claude dentro de wrappers de terceiros) acarreta custo excessivo e desperdício de limites.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       MATRIZ DE ROTEAMENTO DE MODELOS                       │
├─────────────────┬──────────────────────┬────────────────────────────────────┤
│ AGENTE          │ MODELO OBRIGATÓRIO   │ ESCOPO DE ATUAÇÃO                  │
├─────────────────┼──────────────────────┼────────────────────────────────────┤
│ Hermes          │ FREE padrão          │ • Pesquisa na web e docs externas │
│                 │ (sem --provider)     │ • Elaboração de planos em markdown │
│                 │                      │ • Rascunhos de textos legais/FAQ   │
│                 │                      │ • NÃO altera código do repositório │
├─────────────────┼──────────────────────┼────────────────────────────────────┤
│ Antigravity     │ Exclusivo GEMINI     │ • Exploração e leitura profunda    │
│                 │ (Flash / Pro)        │ • Síntese arquitetural e handoffs  │
│                 │                      │ • Documentação estruturada         │
│                 │                      │ • NÃO roteia Claude pago           │
├─────────────────┼──────────────────────┼────────────────────────────────────┤
│ Codex           │ gpt-5.6-luna         │ • Implementação pesada de código   │
│                 │                      │ • Ciclos TDD (teste -> código)     │
│                 │                      │ • Execução de suítes de testes     │
│                 │                      │ • Refatorações e hotfixes pontuais │
├─────────────────┼──────────────────────┼────────────────────────────────────┤
│ Claude          │ haiku                │ • Tarefas mecânicas e automações   │
│                 │                      │ • Geração de stubs repetitivos     │
│                 │                      │ • Conversões simples de formato    │
├─────────────────┼──────────────────────┼────────────────────────────────────┤
│ Claude          │ sonnet               │ • Revisão de segurança e código    │
│                 │                      │ • Integração/merge de branches     │
│                 │                      │ • Orquestração geral do projeto    │
│                 │                      │ • Depuração de bugs complexos      │
├─────────────────┼──────────────────────┼────────────────────────────────────┤
│ Claude          │ opus                 │ • Julgamento arquitetural raro     │
│                 │                      │ • Apenas sob autorização expressa  │
└─────────────────┴──────────────────────┴────────────────────────────────────┘
```

---

## 4. Comandos Exatos de Cada CLI

### 4.1 Hermes (CLI de Pesquisa e Documentação Gratuita)
O Hermes deve ser acionado sempre no modo não-interativo (`-z`), sem parâmetros de provedor pago:

- **Teste de prontidão / cota:**
  ```powershell
  hermes -z "ok"
  ```
- **Execução de plano ou pesquisa com saída direcionada:**
  ```powershell
  hermes -z "Leia as notas no Vault e gere o rascunho de FAQ do Auto Orbital com base nos fluxos reais" > C:\Users\rafae\Documents\Projetos\_tmp\prep\faq-tips.md
  ```
- **Regras estritas para o Hermes:**
  - NUNCA passar flags como `--provider anthropic` ou `--provider openai`.
  - NUNCA solicitar que o Hermes edite código-fonte dentro de `api/`, `frontend/`, `web/` ou `scheduler/`.
  - Saídas do Hermes devem ir exclusivamente para `_tmp/prep/<nome>.md`.

### 4.2 Codex (CLI de Codificação e Testes Autônomos)
O Codex é encarregado de implementar código e rodar testes unitários em worktree isolado:

- **Teste de cota prévia:**
  ```powershell
  codex exec "ping"
  ```
- **Despacho de tarefa com modelo específico em worktree dedicado:**
  ```powershell
  # Exemplo de chamada especificando o modelo padrão de desenvolvimento
  codex exec --model gpt-5.6-luna "Trabalhe no worktree C:\Users\rafae\Documents\Projetos\_tmp\wt-security. Leia .claude/tmp/TAREFAS-AUTONOMAS.md. Corrija o achado F-01 em api/routers/meta_callbacks.py adicionando testes unitários."
  ```
- **Validação de testes locais no ambiente do projeto (dentro do worktree):**
  - **Backend (Python isolado offline):**
    ```powershell
    .venv\Scripts\python.exe -m pytest tests/api --confcutdir=tests/api -q --basetemp=.tmp/pytest-run
    ```
    > [!WARNING]
    > **NUNCA execute `pytest` solto na raiz do repositório.** O arquivo `conftest.py` da raiz inicializa conexões PostgreSQL e aplica migrações no banco Supabase. Utilize sempre a flag `--confcutdir=tests/api` e o diretório restrito `tests/api`.
  - **Frontend (Node + Vite):**
    ```powershell
    cd frontend
    node --test tests/*.mjs
    npm run build
    npm audit
    ```

### 4.3 Antigravity (Pair Programming e Documentação Viva)
O Antigravity atua na camada analítica, documental e de suporte à engenharia com modelos Gemini:

- **Operação no terminal:**
  - Trabalhar rigorosamente no worktree da tarefa designada (ex.: `C:\Users\rafae\Documents\Projetos\_tmp\wt-docs`).
  - Utilizar a tool `run_command` com shells PowerShell padrão, sem executar comandos interativos bloqueantes.
  - Executar tarefas assíncronas apenas quando necessário e monitorar via `manage_task`.
- **Criação de artefatos e relatórios:**
  - Gravar artefatos de documentação consolidada exclusivamente em `docs/` da branch em trabalho.
  - Utilizar a tool nativa `write_to_file` para criações integrais e `replace_file_content` para edições cirúrgicas.

### 4.4 Claude (Orquestrador e Revisor com Subagentes)
Quando o Claude atua como orquestrador principal, ele delega utilizando a ferramenta de subagentes com modelo explícito:

- **Subagente para tarefa mecânica / stub (Haiku):**
  ```json
  {
    "TypeName": "self",
    "Role": "Assistente Mecânico de Sintaxe",
    "Model": "flash_lite",
    "Prompt": "Converta os mapeamentos de constantes para TypeScript estrito no arquivo especificado..."
  }
  ```
- **Subagente para revisão arquitetural ou resolução de conflito (Sonnet):**
  ```json
  {
    "TypeName": "self",
    "Role": "Revisor de Segurança e Integração",
    "Model": "inherit",
    "Prompt": "Analise o diff entre feat/splash-orbital-v2 e staging (34a489a), verificando integridade de hooks e acessibilidade..."
  }
  ```

---

## 5. Regras de Ouro Operacionais

1. **PROIBIDO mexer na `main`:** Toda funcionalidade nova nasce em `feat/<nome>` ou `fix/<nome>` a partir de `staging`. Nenhum agente toca na branch `main`.
2. **PROIBIDO `git push` ou Deploy Direto:** Nenhum comando `git push`, deploy no Render ou ativação de produção deve ser realizado por agentes autônomos sem ordem explícita do Rafa.
3. **PROIBIDO executar SQL de escrita no Supabase real:** Não execute migrações manuais (`051_*.sql`) via script ou conftest no banco real de produção/staging.
4. **PROIBIDO versionar ou imprimir credenciais:** Chaves de API, senhas de banco, tokens OAuth cifrados e segredos internos (`INTERNAL_API_SECRET`) nunca devem aparecer em logs, commits ou saídas de terminal.
5. **Preservação de Design Tokens:** Não crie cores arbitrárias em CSS ou estilos inline. Toda UI deve consumir exclusivamente as variáveis semânticas do design system (`--sky-400`, `--mint-400`, `--graphite-*`, `--brand-*`).
6. **Sincronização com o Vault:** Decisões arquiteturais de impacto devem ser registradas tanto no repositório (`docs/`) quanto no Obsidian Vault do projeto (`Projetos/ShopeeAutoVendas`), mantendo o histórico navegável entre sessões.
