"""
Busca no catálogo real da Shopee (Affiliate Open API) — API Python (FastAPI).

Duplica a lógica pura de busca/categoria de `apis/shopee.py` (mesmo host,
mesma assinatura SHA256, mesma query GraphQL) em vez de importar entre
módulos — mesmo padrão de `api/x_oauth.py`/`api/threads_oauth.py`: evita que
a API nova dependa de `shopee_bot.utils` (apis/shopee.py importa
`retry_with_backoff`/`ReturnableThread` no nível do módulo só por causa das
funções de scraping/publicação do Flask legado).

Diferença deliberada do legado: aqui a busca tenta primeiro um conjunto de
campos "rico" (sales/ratingStar/shopName/commissionRate) que a documentação
de terceiros da Shopee Affiliate API sugere existir em `productOfferV2`, mas
que NUNCA foi confirmado contra a API real deste projeto (nenhuma chamada
anterior no código pediu esses campos — ver `apis/shopee.py::query_search`,
que só usa os 7 campos mínimos). Se a Shopee responder com erro de schema
("Cannot query field..."), a busca refaz a chamada só com os campos mínimos
confirmados — nunca falha por causa de um campo extra especulativo.
"""

import hashlib
import json
import time

import httpx

SHOPEE_GRAPHQL_URL = "https://open-api.affiliate.shopee.com.br/graphql"
SHOPEE_CATEGORY_URL = "https://seller.shopee.com.br/help/api/v3/global_category/list/"

# sort_type (Open API): 1=Relevância, 2=Vendas, 3=Preço↓, 4=Preço↑,
# 5=Comissão↓. A API não tem opção de "mais recentes" — não inventar.
VALID_SORT_TYPES = frozenset({1, 2, 3, 4, 5})

# Campos confirmados em uso no restante do projeto (ver apis/shopee.py) —
# sempre disponíveis, é o fallback garantido.
_MINIMAL_FIELDS = (
    "itemId", "offerLink", "productName", "productLink",
    "imageUrl", "priceMax", "priceMin", "commission",
)

# Best-effort: sugeridos por documentação de terceiros do schema
# `productOfferV2`, nunca testados contra a API real (sem credencial de
# teste disponível neste projeto — ver relatório da tarefa que introduziu
# este módulo). Se a Shopee rejeitar, cai pro conjunto mínimo acima.
_RICH_EXTRA_FIELDS = ("sales", "ratingStar", "shopName", "commissionRate")


class ShopeeCatalogError(Exception):
    """Falha ao falar com a Shopee (rede, resposta inesperada, schema).

    `errors`: lista crua de erros GraphQL retornados pela Shopee, quando
    aplicável (vazia pra falha de rede/HTTP) — usado por quem chama pra
    decidir se é um erro de schema (campo desconhecido) que justifica
    fallback, sem precisar re-parsear a mensagem da exceção.
    """

    def __init__(self, message: str, errors: list[dict] | None = None):
        super().__init__(message)
        self.errors = errors or []


class ShopeeAuthError(ShopeeCatalogError):
    """Credencial (app_id/secret) inválida ou sem permissão."""


class ShopeeRateLimitError(ShopeeCatalogError):
    """Shopee limitou a taxa de chamadas (HTTP 429 ou código 10030)."""


def _gen_authorization(app_id: str, secret: str, payload: str) -> str:
    timestamp = int(time.time())
    sign_factor = f"{app_id}{timestamp}{payload}{secret}"
    signature = hashlib.sha256(sign_factor.encode()).hexdigest()
    return f"SHA256 Credential={app_id}, Timestamp={timestamp}, Signature={signature}"


def _is_unknown_field_error(errors: list[dict]) -> bool:
    return any(
        "cannot query field" in (err.get("message") or "").lower()
        for err in errors
    )


# Códigos de erro (`errors[].extensions.code`) da Shopee Affiliate Open API
# (tabela "Error Codes" documentada em github.com/bcat95/shopee-aff):
# 10020 = assinatura/credencial/timestamp inválidos ou app desativado;
# 10031..10035 = acesso negado / afiliado inválido, congelado, bloqueado ou
# sem acesso à Open API — todos exigem ação do usuário na credencial.
_AUTH_EXTENSION_CODES: frozenset[int] = frozenset({10020, 10031, 10032, 10033, 10034, 10035})
# 10030 = rate limit da Shopee — não é problema de credencial.
_RATE_LIMIT_EXTENSION_CODES: frozenset[int] = frozenset({10030})


def _has_code(errors: list[dict], codes: frozenset[int]) -> bool:
    return any((err.get("extensions") or {}).get("code") in codes for err in errors)


def _is_auth_error(errors: list[dict]) -> bool:
    return _has_code(errors, _AUTH_EXTENSION_CODES)


def summarize_errors(errors: list[dict]) -> list[dict]:
    """Só `message` + `extensions.code` de cada erro GraphQL — seguro pra
    log (a Shopee não ecoa app_id/secret/assinatura nesses campos)."""
    return [
        {"message": (err.get("message") or "")[:300], "code": (err.get("extensions") or {}).get("code")}
        for err in errors
    ]


async def _post_graphql(app_id: str, secret: str, query: str, variables: dict) -> dict:
    """POST autenticado no GraphQL da Shopee. Retorna `data` em caso de
    sucesso. Levanta `ShopeeAuthError` só para HTTP 401/403 ou erro GraphQL
    com `extensions.code` de credencial/assinatura conhecido; qualquer outra
    falha (429, 5xx, JSON inválido, erro GraphQL sem código reconhecido) cai
    em `ShopeeCatalogError` genérico — evita mostrar "credencial inválida"
    pra rate limit ou instabilidade da própria Shopee."""
    payload = json.dumps({
        "operationName": None,
        "query": query,
        "variables": variables,
    })
    headers = {
        "Content-Type": "application/json",
        "Authorization": _gen_authorization(app_id, secret, payload),
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(SHOPEE_GRAPHQL_URL, content=payload, headers=headers)
    except httpx.RequestError as exc:
        raise ShopeeCatalogError(f"Falha de rede ao chamar a Shopee: {exc}") from exc

    if resp.status_code in (401, 403):
        raise ShopeeAuthError(
            f"Shopee respondeu {resp.status_code} — credencial inválida ou sem permissão."
        )
    if resp.status_code == 429:
        raise ShopeeRateLimitError("Shopee respondeu 429 — limite de chamadas atingido.")
    if resp.status_code != 200:
        raise ShopeeCatalogError(
            f"Shopee respondeu {resp.status_code} — tente novamente mais tarde."
        )

    try:
        body = resp.json()
    except ValueError as exc:
        raise ShopeeCatalogError("Resposta inesperada da Shopee (JSON inválido).") from exc

    errors = body.get("errors")
    if errors:
        if _is_auth_error(errors):
            raise ShopeeAuthError(f"Shopee rejeitou a credencial/assinatura: {errors}", errors=errors)
        if _has_code(errors, _RATE_LIMIT_EXTENSION_CODES):
            raise ShopeeRateLimitError(f"Shopee limitou as chamadas: {errors}", errors=errors)
        raise ShopeeCatalogError(f"Shopee retornou erros GraphQL: {errors}", errors=errors)
    if "data" not in body:
        raise ShopeeCatalogError("Resposta inesperada da Shopee (sem campo 'data').")
    return body["data"]


# Máximo de itens por chamada que usamos na Shopee (a doc não publica teto
# pro productOfferV2; 50 é o maior valor usado por integrações de
# referência). Pedidos maiores viram várias páginas (`page`).
SHOPEE_PAGE_LIMIT = 50


def _build_search_query(
    fields: tuple[str, ...],
    *,
    has_keyword: bool,
    product_cat_id: int | None,
    sort_type: int,
    page: int,
    limit: int,
) -> str:
    """Query GraphQL de `productOfferV2`.

    `keyword` (texto livre do usuário) entra SÓ via variável `$kw` — nunca
    interpolado na string (ver MEDIUM-1 do relatório de segurança). Os
    argumentos numéricos entram como literais inteiros (já validados como
    `int` por quem chama — sem risco de injeção): declarar variável com o
    tipo errado quebra a validação GraphQL inteira. Era a causa do 502 em
    produção — `$cat: Int64` contra `productCatId: Int32` no schema da
    Shopee. Literal inteiro serve pra qualquer escalar inteiro, e
    `productCatId` só vai na query quando há categoria."""
    args = []
    if has_keyword:
        args.append("keyword: $kw")
    if product_cat_id is not None:
        args.append(f"productCatId: {int(product_cat_id)}")
    args.append(f"sortType: {int(sort_type)}")
    args.append(f"page: {int(page)}")
    args.append(f"limit: {int(limit)}")
    signature = "query($kw: String)" if has_keyword else "query"
    fields_block = "".join(f"      {f}\n" for f in fields)
    return (
        f"{signature} {{"
        f"  productOfferV2({', '.join(args)}) {{"
        "    nodes {\n"
        f"{fields_block}"
        "    }"
        "  }"
        "}"
    )


async def _search_page(
    app_id: str, secret: str, *, keyword: str | None, product_cat_id: int | None,
    sort_type: int, page: int, limit: int,
) -> list[dict]:
    """Uma página do productOfferV2. Tenta o conjunto de campos "rico"
    primeiro; se a Shopee rejeitar por schema (`Cannot query field...`),
    refaz com o conjunto mínimo garantido."""
    variables = {"kw": keyword} if keyword else {}
    common = dict(
        has_keyword=bool(keyword), product_cat_id=product_cat_id,
        sort_type=sort_type, page=page, limit=limit,
    )
    try:
        data = await _post_graphql(
            app_id, secret, _build_search_query(_MINIMAL_FIELDS + _RICH_EXTRA_FIELDS, **common), variables,
        )
    except ShopeeAuthError:
        raise
    except ShopeeCatalogError as exc:
        if not _is_unknown_field_error(exc.errors):
            raise
        data = await _post_graphql(app_id, secret, _build_search_query(_MINIMAL_FIELDS, **common), variables)
    return (data.get("productOfferV2") or {}).get("nodes") or []


async def search_products(
    app_id: str,
    secret: str,
    *,
    keyword: str | None = None,
    product_cat_id: int | None = None,
    sort_type: int = 1,
    limit: int = 20,
    page: int = 1,
) -> list[dict]:
    """Busca produtos no catálogo real da Shopee. `limit` acima de
    `SHOPEE_PAGE_LIMIT` é atendido em várias páginas sequenciais a partir
    de `page`, parando quando uma página vem incompleta (fim dos
    resultados)."""
    nodes: list[dict] = []
    current = page
    # Tamanho de página constante: `page` da Shopee é relativo ao `limit`.
    per_page = min(SHOPEE_PAGE_LIMIT, limit)
    while len(nodes) < limit:
        batch = await _search_page(
            app_id, secret, keyword=keyword, product_cat_id=product_cat_id,
            sort_type=sort_type, page=current, limit=per_page,
        )
        nodes.extend(batch)
        if len(batch) < per_page:
            break
        current += 1
    return nodes[:limit]


async def _get_global_category_list(page: int, size: int = 1000) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                SHOPEE_CATEGORY_URL, params={"page": page, "size": size},
            )
    except httpx.RequestError as exc:
        raise ShopeeCatalogError(f"Falha de rede ao buscar categorias da Shopee: {exc}") from exc

    if resp.status_code != 200:
        return None
    body = resp.json()
    return body.get("data")


# Árvore de categorias muda raramente — cache em memória de processo com
# TTL (mesmo padrão simples de dict módulo-level usado em auth.py pros
# cooldowns). Evita percorrer a árvore inteira em seller.shopee.com.br a
# cada chamada do endpoint (ver MEDIUM-2 do relatório de segurança).
_CATEGORY_CACHE_TTL_SECONDS = 3600
_category_cache: dict = {"data": None, "expires_at": 0.0}

# Limite de páginas do loop de paginação: sem isso, uma resposta com
# `global_cats` vazio antes de `items_parsed` atingir `total` faria o
# `while True` original pedir página pra sempre (ver MEDIUM-2). Este número
# é bem maior que a árvore de categorias real da Shopee costuma precisar.
_MAX_CATEGORY_PAGES = 50


async def get_category_list() -> list[dict]:
    """Árvore de categorias da Shopee (`seller.shopee.com.br`, REST simples,
    sem autenticação de afiliado) — usada como filtro de categoria no
    frontend. Mesma lógica de `apis/shopee.py::get_category_list`, sem
    dependência de `shopee_bot.*`. Cacheada (ver `_CATEGORY_CACHE_TTL_SECONDS`)
    e com paginação limitada/tolerante a resposta incompleta (ver
    `_MAX_CATEGORY_PAGES`) — nunca lança `KeyError` cru por `total`/
    `global_cats` ausentes."""
    now = time.monotonic()
    if _category_cache["data"] is not None and now < _category_cache["expires_at"]:
        return _category_cache["data"]

    total = 0
    items_parsed = 0
    page = 1
    categories: list[dict] = []
    seen_ids: set = set()

    while page <= _MAX_CATEGORY_PAGES:
        res = await _get_global_category_list(page)
        if res is None:
            raise ShopeeCatalogError("Falha ao buscar categorias da Shopee.")

        global_cats = res.get("global_cats") or []
        if not global_cats:
            break

        if total == 0:
            total = res.get("total") or 0

        for cat in global_cats:
            old_category_id = None
            for index, item in enumerate(cat.get("path") or []):
                category_id = item.get("category_id")
                if category_id is not None and category_id not in seen_ids:
                    categories.append({
                        "name": item.get("category_name"),
                        "category_id": category_id,
                        "parent_id": old_category_id if index > 0 else None,
                    })
                    seen_ids.add(category_id)
                old_category_id = category_id
            items_parsed += 1

        if total and items_parsed >= total:
            break
        page += 1

    _category_cache["data"] = categories
    _category_cache["expires_at"] = now + _CATEGORY_CACHE_TTL_SECONDS
    return categories
