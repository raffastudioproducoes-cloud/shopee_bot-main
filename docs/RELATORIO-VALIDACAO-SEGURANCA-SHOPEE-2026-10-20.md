# Auto Orbital - relatorio de validacao de seguranca para a Shopee

Data: 20/10/2026 (America/Sao_Paulo). Produto em beta fechado.

**Resultado do escopo executado: aprovado.** Este documento registra as evidencias tecnicas de correcao e reteste. Ele nao substitui a decisao de aceitacao da Shopee nem afirma ausencia absoluta de vulnerabilidades futuras.

## Escopo e metodo

Foram revisados os 54 avisos historicos da matriz de dependencias, o codigo autenticado, a configuracao de proxy, o armazenamento de midia, as rotas administrativas e a superficie publica. Os testes combinaram suite automatica, auditoria de dependencias, build/deploy no Render, consultas de seguranca do Supabase e exercicios em staging com contas sinteticas descartadas apos uso.

## Resultado consolidado

| Area | Resultado | Evidencia |
| --- | --- | --- |
| Matriz historica | Aprovada | Os 54 IDs possuem pin atual igual ou superior a versao corretiva anotada na matriz. |
| Dependencias | Aprovada | pip-audit dos requirements e npm audit --omit=dev --audit-level=high sem vulnerabilidades conhecidas. |
| Regressao de API | Aprovada | 837 testes de tests/api aprovados no ambiente Python 3.13 isolado. |
| Camada web | Aprovada | 8 testes de CSP/proxy aprovados; build TypeScript/Vite aprovado. |
| Sessao e acesso | Aprovada | Logout, troca de senha e revogacao de token foram retestados em staging; repeticao de token revogado retornou 401. |
| Separacao de contas e perfis | Aprovada | Contas sinteticas nao acessaram rascunho, perfil, lista ou backup de outro escopo. |
| Administracao | Aprovada | USER recebeu 403 nas rotas administrativas; ADMIN temporario recebeu 200 nas rotas autorizadas. |
| Midia | Aprovada | Upload valido passou, MIME invalido foi recusado e URL publica sem autorizacao para midia privada retornou 400. |
| CSRF e CORS | Aprovada | Mutacao autenticada com origem externa foi recusada com 403. |
| Superficie publica | Aprovada | /api/docs e /api/openapi.json retornaram 404; endpoints publicos testados entregaram script-src self. |

## Dependencias e os 54 avisos

A matriz MATRIZ-54-ALERTAS.csv contem 1 alerta Critical, 26 High, 22 Moderate e 5 Low, em cinco lotes. A comparacao automatizada da matriz contra os pins atuais retornou **54 de 54** em versao corrigida ou superior.

- PyJWT: 15 IDs, pin 2.15.0; decodificacao exclusiva HS256, rejeicao de crit, algoritmos alternativos e chaves assimetricas cobertas por regressao.
- python-multipart: 7 IDs, pin 0.0.31; parser e limites de upload cobertos.
- Pillow: 18 IDs, pin 13.0.0; saneamento e validacao de imagem cobertos.
- urllib3, requests e idna: 8 IDs, pins 2.8.0, 2.33.0 e 3.15; regressao de redirect, descompressao, TLS e entradas IDNA coberta.
- Flask, Werkzeug e python-dotenv: 6 IDs, pins 3.1.3, 3.1.9 e 1.2.2.

O build de staging do commit 46e1f75 concluiu no Render e ficou live. A imagem instala os dois arquivos de requirements antes de copiar o codigo; os pins acima sao, portanto, o conjunto usado pelo build implantado.

## Exercicios reais em staging

As contas usadas nos testes foram criadas apenas para esta validacao e removidas no final. Nenhuma conta de terceiro foi alterada.

- Registro, login e leitura da sessao: 201/200/200.
- Rate limit de login: seis tentativas invalidas retornaram 401, 401, 401, 401, 401, 429, inclusive quando o cabecalho de IP variou.
- Logout e troca de senha invalidaram a sessao anterior; o token reaproveitado recebeu 401.
- Limite de tres perfis, compartilhamento correto de catalogo e isolamento de listas/restauracao de backup foram verificados; backup de outro perfil e backup adulterado foram recusados com 400.
- Usuario comum recebeu 403 nas rotas administrativas; conta temporariamente elevada recebeu 200 nas rotas de metricas, credenciais, logs e usuarios.
- Midia privada sem sessao recebeu 400. Conta de outra origem recebeu 404 ao tentar alterar rascunho ou perfil que nao lhe pertence.

O painel de staging preserva evidencias de publicacoes reais concluidas em Threads, Facebook e Instagram pela conta administrativa. Elas registram estado Publicado; os testes de credencial das tres redes e do TikTok foram verificados no painel. X permanece sem conexao/credito do provedor, portanto nao foi usado para uma nova publicacao. Essa indisponibilidade externa nao mascara falha de autorizacao no aplicativo e deve ser resolvida na conta X antes de usar essa rede em producao.

## Plataforma e configuracao

- JWT usa somente HS256 com chave de ambiente; o algoritmo do token nao e aceito como configuracao do servidor.
- Cookies sao HttpOnly, Secure e SameSite=Lax.
- Logs sanitizam contexto de erro e redirect, sem gravar tokens, senhas, chaves de API ou hashes sensiveis.
- O advisor de seguranca do Supabase encontrou cinco tabelas internas com RLS habilitado e sem policy. Isso bloqueia acesso pelo cliente anonimo; elas sao acessadas apenas pelo backend com credencial de servidor.
- O advisor de desempenho apontou chaves estrangeiras sem indice em filas e sessoes. Nao e falha de seguranca e ficou fora deste pentest; sera tratado na etapa planejada de escala, com medicao antes de criar indices.

## Limites conhecidos e acompanhamento

1. style-src unsafe-inline permanece por compatibilidade visual de templates legados. Scripts inline e unsafe-eval foram removidos das rotas publicas testadas. A reducao adicional de estilos exige migracao visual separada para nao quebrar telas legadas.
2. O limitador de login e consistente entre IPs no processo implantado. Em futura escala horizontal deve ser movido para armazenamento compartilhado, por exemplo Redis, para manter o mesmo limite entre replicas.
3. O Render nao fornece shell na instancia gratuita. A evidencia da imagem e composta por build aprovado, pins versionados e auditoria do ambiente isolado; um SBOM de sistema operacional fica recomendado para a proxima rodada de conformidade.

## Conclusao

As vulnerabilidades e controles incluidos neste escopo foram corrigidos e retestados sem falhas conhecidas. O sistema esta apto para encaminhamento tecnico a Shopee como beta fechado. Mudancas futuras de dependencias, infraestrutura, OAuth ou superficie publica exigem nova rodada proporcional de auditoria antes de producao aberta.

Historico: RELATORIO-PENTEST-SHOPEE-2026-10-17.md. Matriz por ID: MATRIZ-54-ALERTAS.csv.
