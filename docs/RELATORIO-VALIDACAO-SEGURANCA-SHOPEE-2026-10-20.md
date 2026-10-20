# Auto Orbital - validacao de seguranca para a Shopee

Data: 20/10/2026 (America/Sao_Paulo). Produto em beta fechado.
**Parecer: remediacao de dependencias comprovada; pentest integral ainda nao
aprovado.** Este relatorio registra resultados verificaveis e lacunas. Nao e
um certificado de ausencia de vulnerabilidades nem garante aprovacao pela Shopee.

## Escopo e metodo

Revisao do codigo, dos 54 avisos historicos em `MATRIZ-54-ALERTAS.csv`,
testes automatizados, build Docker no Render, verificacoes HTTP de baixo
impacto e um ciclo de navegador com conta sintetica em staging. Os 54 avisos
sao sobre versoes de bibliotecas; nao representam 54 exploracoes confirmadas.
Staging e producao compartilham o Supabase. Nao houve teste de carga,
publicacao social nem acesso a dados de terceiros.

## Evidencias positivas

| Controle | Resultado verificado |
| --- | --- |
| Dependencias Python | Os 54 IDs da matriz tem pin atual igual ou superior a versao de correcao citada; revisao por grupo e caminhos de chamada. O `pip freeze` do estagio Python final do Docker apareceu nos logs dos builds de staging e producao. |
| Versoes instaladas nos dois builds | PyJWT 2.15.0; python-multipart 0.0.31; Pillow 12.3.0; requests 2.33.0; urllib3 2.8.0; idna 3.15; Flask 3.1.3; Werkzeug 3.1.9; python-dotenv 1.2.2; FastAPI 0.143.3; Starlette 1.8.0. |
| Regressao local | 834 testes da API aprovados; 7 testes focados do proxy/CSP aprovados; build TypeScript/Vite aprovado. O CI de `main` passou em `685c71e`. |
| Sessao e isolamento | Retestes anteriores em staging: replay do cookie apos logout/troca de perfil retornou 401; acesso a listas/perfis de outro escopo retornou 404; origem externa em mutacao com cookie retornou 403. Contas sinteticas foram excluidas. |
| Navegador staging | Login React abriu sem erro no console sob a nova CSP. Conta descartavel: cadastro 201, login 200, consulta de sessao 200, criacao de perfil 201, exclusao 200. Consulta posterior ao banco: zero contas `codexpt-browser-%`. |
| API real de staging, duas contas | Cadastro, login e consulta de sessao 201/200/200 em ambas; usuario comum em `/admin/metrics` 403; escrita com cookie e origem externa 403; criacao de perfil e upload PNG em rascunho 201; tentativa da conta B de ativar perfil ou excluir rascunho da conta A 404; exclusao pelo dono 200; replay do cookie apos logout 401. Ambas as contas foram excluidas (200); consulta posterior encontrou zero usuarios `codexpt-real-%`. O primeiro upload com MIME `application/octet-stream` retornou 415 corretamente; o reteste com `image/png` passou. |
| API real de staging, papel ADMIN | Uma conta descartavel foi elevada temporariamente no banco: login 200 e `/admin/metrics` 200. Foi rebaixada para USER e excluida (200); consulta posterior encontrou zero usuarios `codexpt-admin-%`. Nenhuma conta existente foi modificada. |
| Superficie publica | Producao: `/` 200 com `script-src 'self'`, `/splash.js` 200, `/api/health/ready` 200, `/api/auth/me` sem cookie 401, `/api/docs` e `/api/openapi.json` 404. |
| Deploy | Staging `ba16d63` (`dep-dbbpvgqvcj2c73dp30r0`) e producao `685c71e` (`dep-dbbq4e17lnhs73fll8e0`) em estado `live`; CI/CD de main concluidos com sucesso. |

O `pip freeze` no Dockerfile registra o grafo Python resolvido depois da
instalacao das duas listas de requirements e antes de copiar o codigo.
Isso comprova as versoes de Python naquele build, mas nao inventaria pacotes
do sistema operacional, digest da imagem ou mudancas posteriores de runtime.
A matriz historica continua sendo o anexo por ID; os seus campos `Estado`
descrevem o plano original e nao foram sobrescritos para simular retestes.

## Correcoes desta rodada

- A SPA nao autoriza mais JavaScript inline em `script-src`; o fallback de
  inicializacao foi movido para `/splash.js` e o `onclick` foi removido.
- `FLASK_DEBUG=False` agora e interpretado como falso, evitando resposta
  detalhada por conversao incorreta de string para booleano.
- Testes de CSP e da origem no proxy passaram a bloquear regressao no CI.
- O Dockerfile publica no log de build a lista de distribuicoes Python
  instaladas, sem imprimir chaves ou variaveis de ambiente.

## Lacunas e risco residual

1. **CSP parcial:** `style-src` ainda permite `unsafe-inline`; paginas Jinja
   legadas ainda permitem script inline. A SPA foi verificada em navegador,
   mas nao houve migracao e teste visual de todas as telas legadas.
2. **Fluxos externos nao exercitados:** nao houve OAuth real de cada rede,
   assinatura de webhook real, publicacao social ou teste browser de CSRF
   entre origens com esses fluxos. Testes unitarios mockados nao equivalem
   a esses cenarios.
3. **Escopo autenticado incompleto:** os retestes reais cobriram o acesso
   positivo/negativo a uma rota ADMIN e a autorizacao de rascunho de midia
   pelo backend. Nao cobriram todas as rotas ADMIN, acesso direto ao bucket
   do Storage, nem toda a suite Flask dependente de Postgres de teste.
4. **Inventario parcial:** o Render gratuito nao oferece shell na instancia.
   O grafo Python foi observado no build final, mas nao foi obtido SBOM
   completo da imagem ativa nem inventario de pacotes do sistema. A API
   Dependabot do repositorio respondeu 403 (alertas desativados); portanto
   esta matriz nao e um feed vivo de novos avisos.

## Decisao

**Nao enviar como relatorio final verde.** Os 54 avisos historicos estao
remediados no componente Python por versao instalada nos dois builds;
isso nao encerra o pentest integral nem comprova ausencia de outros riscos.
Para um parecer final favoravel: testar os fluxos externos e as demais rotas
ADMIN/Storage em ambiente controlado, revisar a CSP das telas
legadas, obter inventario completo da imagem e repetir a auditoria de
vulnerabilidades atual. A aceitacao formal depende dos criterios da Shopee.

Historico detalhado das correcoes e dos retestes anteriores:
`RELATORIO-PENTEST-SHOPEE-2026-10-17.md`.
