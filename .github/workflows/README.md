# GitHub Actions — CI/CD para ShopeeAutoVendas
> Estrutura de automação contínua de integração e entrega contínua.
> Foi criado em 2026-09-04 na migração para React + API Python + Supabase.
> Esta pasta deve conter os arquivos `.yml` dos workflows do GitHub Actions.
> Cada workflow é acionado por eventos do repositório e executa tarefas de
> verificação, teste, build e deploy conforme a configuração.

## Arquivos

- `ci.yml` — pipeline de integração contínua: lint + test para a API Python.
- `cd.yml` — pipeline de entrega contínua: deploy no Render (se houver integração).

## Como usar

1. Verifique se há um arquivo `.env.example` no repositório.
2. Configure as variáveis de ambiente no GitHub Actions (Settings → Secrets).
3. Atualize os arquivos `.yml` conforme necessário.

## Configuração do GitHub Actions

Para configurar o GitHub Actions, vá em `Settings → Actions → General` e habilite
os permalink para comandos de pull request.

## Secrets

As seguintes variáveis de ambiente são necessárias:

- `SUPABASE_URL` — URL do projeto Supabase.
- `SUPABASE_KEY` — API key (service role ou anon).
- `FLASK_SESSION_SECRET` — chave secreta da sessão Flask.
- `APP_ENCRYPTION_KEY` — chave de criptografia da aplicação.
- `GEMINI_API_KEY` — chave da API Gemini.

## Regras de uso

1. Sempre use branches de feature para novas funcionalidades.
2. Sempre faça o commit das mudanças antes de submeter um pull request.
3. Sempre faça o push para o repositório remoto antes de abrir um pull request.
4. Sempre revise os arquivos `.yml` antes de commitar.
5. Sempre teste os pipelines localmente antes de submeter.

## Atualização

Este arquivo é atualizado manualmente. Para atualizar, edite o arquivo e faça o commit
com uma mensagem descritiva.

## Referências

- [GitHub Actions](https://docs.github.com/en/actions)
- [Supabase](https://supabase.com/docs)
- [Render](https://render.com/docs)

## Autores

- Rafa Studio Producoes (Rafael Machado Galvão)
