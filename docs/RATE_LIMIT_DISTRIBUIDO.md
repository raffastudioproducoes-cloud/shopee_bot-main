# Rate limiting distribuído (Redis/Render Key Value)

## Garantias e comportamento

- Flask-Limiter: teto global **200/h e 50/min por IP** compartilhado entre workers quando `RATELIMIT_STORAGE_URI` aponta para Redis.
- FastAPI: login **5 tentativas/60s por username normalizado**, reset de senha **1 tentativa/60s por username** e cadastro **1 tentativa/30s por IP**. O Redis executa uma operação atômica por tentativa; múltiplos workers não multiplicam os limites.
- A identidade é gravada como SHA-256 na chave, sem username ou IP em texto claro. Redis é usado exclusivamente para contadores efêmeros (TTL).
- Com URI Redis configurada e armazenamento indisponível, endpoints de autenticação retornam **HTTP 503** sem vazar dados da conexão (fail closed). A camada Flask usa limites locais de contingência para manter páginas não autenticadas disponíveis.
- Sem URI (desenvolvimento/testes) mantém-se a implementação em memória. Não use esse fallback no Render escalado.

## Configuração por ambiente

Criar um Render Key Value **na mesma região** do web service e obter a **Internal Redis URL** em *Key Value → Connect*. Não expor a URI em commits, logs, documentação ou frontend. Configurar em **Render → Environment**, separadamente para staging e produção:

| Variável | Exemplo | Finalidade |
| --- | --- | --- |
| `RATELIMIT_STORAGE_URI` | URI interna da instância Key Value, definida como segredo | Redis compartilhado |
| `RATELIMIT_KEY_PREFIX` | `auto-orbital:staging` ou `auto-orbital:production` | Isolamento de contadores |

A URL deve começar com `redis://` ou `rediss://`. Para planos gratuitos de Key Value, aceite o caráter **não persistente** dos contadores: um reboot libera cooldowns existentes, mas os contadores voltam a ser compartilhados ao iniciar. Para controles mais rígidos, usar plano com persistência; avaliar preço antes.

## Validação e promoção

1. Merge do código e testes em **staging**; aguardar deploy **live** e `/health` HTTP 200.
2. Configurar URI **no staging**, aguardar redeploy, verificar login de teste e limites 429, e simular falha de Redis com isolamento controlado sem interromper produção.
3. Confirmar métricas de erro e ausência de vazamento de credenciais nos logs.
4. Só então promover o mesmo código para **main** e criar Key Value separado na região de produção; configurar **a URI interna da produção** antes de validar login e limites. Manter isolados ambos os contadores.
5. Em incidente, restaurar conectividade Redis. Retirar `RATELIMIT_STORAGE_URI` causa degradação para memória, que só é aceitável temporariamente com **uma única instância**.

Os testes unitários da API estão em `tests/api/test_distributed_rate_limit.py` e a pipeline CI roda para PR/push em **main** e **staging**.
