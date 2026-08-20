# Módulo Web
Esse módulo é responsável pela interface gráfica que permite o gerencimento de usuários, produtos,
lista de produtos, credenciais das plataformas dos bots, horários dos trabalhos do scheduler, etc.
Por enquanto apenas funciona com a [Shopee](https://affiliate.shopee.com.br/) porém a intenção é
expandir para outras como a Amazon, Mercado Livre etc.

Implementado em Flask[^1], também permite fazer uso de algumas funcionalidades do Scheduler[^2]
através de um painel de gerenciamento. As principais tecnologias utilizadas são:
- [Gunicorn](https://docs.gunicorn.org/en/stable/)
- [Flask-Session](https://flask-session.readthedocs.io/en/latest/)
- [Flask-Login](https://flask-login.readthedocs.io/en/latest/)
- [Flask-WTF](https://flask-wtf.readthedocs.io/en/latest/)
- [Tailwindcss](https://tailwindcss.com/docs)
- [Alpine.js](https://alpinejs.dev/start-here)

## Estrutura do Projeto
    forms/              <- classes de validação dos formulários
    media/              <- onde as mídias dos produtos ficam salvas
    routes/
    static/
    templates/          <- cada pasta representa uma rota/domínio
    __init__.py         <- server
    helpers.py
    user.py             <- usado pelo flask-login


## Rotas
    # página privada
    GET  /

    # Autorização - páginas públicas
    GET  /auth/login
    GET  /auth/logout
    POST /auth/login

    # Atividades
    GET  /activities                        log de atividades do bot/agendador

    # Painel
    GET  /panel/profile
    POST /panel/profile/new-password
    GET  /panel/credentials
    POST /panel/credentials/shopee
    DEL  /panel/credentials/shopee
    POST /panel/credentials/threads
    DEL  /panel/credentials/threads
    POST /panel/credentials/twitter
    DEL  /panel/credentials/twitter/<id>

    GET  /panel/schedulers                  visualização dos trabalhos agendados
    POST /panel/schedulers/collect-product  coleta os produtos da listas ativas por demanda
    POST /panel/schedulers/<id>             atualiza configuração de um trabalho agendado
    PUT  /panel/schedulers/<id>/active      desativa/ativa trabalho agendado

    # Lista de produtos
    GET  /product-lists
    GET  /product-lists/add
    GET  /product-lists/<id>
    POST /product-lists
    PUT  /product-lists/<id>
    DEL  /product-lists/<id>

    # Produtos
    GET  /products
    GET  /products.json
    GET  /products/add
    GET  /products/<id>
    POST /products
    PUT  /products/<id>
    PUT  /products/<id>/update              atualiza os dados do produto
    DEL  /products/<id>

    # Usuários
    GET  /users
    GET  /users/add
    GET  /users/<id>
    POST /users
    PUT  /users/<id>
    DEL  /users/<id>

[^1]: [Flask](https://flask.palletsprojects.com/en/stable/)
[^2]: [Scheduler](./../scheduler/README.md)
