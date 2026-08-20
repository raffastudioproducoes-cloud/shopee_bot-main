# Módulo Scheduler (Agendamento)
Esse módulo é responsável por todas as tarefas agendadas da plataforma. Faz uso do Database[^1]
para determinar se alguma tarefa deve ser executada ou não a nível de usuário, validando todos
os dados necessários para a tarefa. É possível configurar a frequência e se devem ou não ser
executadas a partir do painel de gerenciamento do usuário.

Tarefas existentes:
- Bot Post
- Collect Products
- Update Products

## Bot Post
Faz a postagem nas plataformas que o usuário disponibilizou credenciais a partir das listas ativas
de produtos.

## Collect Products
É executada sempre que a lista de produtos de algum bot acaba ou por demanda pelo painel de
gerenciamento do usuário. Apenas coleta produtos das listas ativas.

## Update Products
Atualiza os dados dos produtos cadastrados uma vez por semana.

[^1]: [Database](./../database/README.md)
