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

## Publicações seguras durante deploy (incidente 30–31/10/2026)

A mesma aplicação web Render Free hospeda o scheduler APScheduler (PostgreSQL
compartilhado com produção/staging). Um `git push` não interrompe a postagem:
quem interrompe é a troca da instância na etapa de deploy.

1. `execute_publication` adquire lease de `publication_claims` e enfileira
   `publish_jobs` com chave única por ocorrência. `claim` é uma operação
   atômica com `FOR UPDATE SKIP LOCKED`, garantindo um único executor.
2. Enquanto prepara dados e mídia, a publicação ainda não saiu do servidor.
   Cada publicador chama `mark_external_delivery()` **antes** do primeiro
   endpoint mutável (criação de contêiner, upload ou publicação), persistindo
   `external_started_at` apenas com o `claim_token` vigente.
3. Se o worker for encerrado antes do envio, `PublicationDeferred` sai do
   publicador sem ser engolida por `except Exception`. A fila retorna a
   `pending` somente se `external_started_at IS NULL`; o coletor periódico
   recupera leases abandonados pré-envio, com limite de cinco tentativas de
   recuperação por expiração.
4. Depois do primeiro contato externo, uma queda pode significar postagem
   efetiva sem resposta. O estado vai para `unknown`, **sem retry cego**.
   Os posts desconhecidos exigem conciliação via painel/API, nunca exclusão
   automática para limpar indicador.
5. O worker `PublishingGeventWorker` recebe SIGTERM, bloqueia novos disparos,
   deixa o Gunicorn sair do loop e, **antes do worker desaparecer**, drena o
   scheduler aguardando os trabalhos ativos. O timeout de shutdown do Render
   ainda é limite rígido: SIGKILL não é recuperável no processo.

As migrações aditivas `060_track_external_publish_start.sql` e\n`061_guard_legacy_publish_leases.sql` registram a barreira e distinguem\nclaims da versão antiga da produção. A migração 060 marca como
potencialmente externos todos os jobs `running` de versões antigas, evitando
republicação após o upgrade. Não modificar a coluna para NULL em produção.

### Testar sem postar na rede

```bash
python -m pytest tests/scheduler --confcutdir=tests/scheduler -q
```

`test_deploy_safe_publications.py` simula SIGTERM entre preparação e rede,
perda de claim, retomada pré-envio e vedação de retry depois de cruzar a
fronteira externa. Os testes são mockados; **não** exigem credenciais de
Threads/Meta e não representam publicação real. Como o Supabase é compartilhado
pelos ambientes, não executar testes de integração que mutem jobs reais.
