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


async def _post_graphql(app_id: str, secret: str, query: str) -> dict:
    """POST autenticado no GraphQL da Shopee. Retorna `data` em caso de
    sucesso; levanta `ShopeeAuthError` em falha HTTP (credencial inválida na
    prática — a Shopee não documenta um corpo de erro estável pra distinguir
    "assinatura errada" de outras falhas 4xx/5xx) e `ShopeeCatalogError` com
    a lista de erros GraphQL quando a resposta tem `errors` (inclusive erro
    de schema desconhecido, tratado por quem chama)."""
    payload = json.dumps({
        "operationName": None,
        "query": query,
        "variables": None,
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

    if resp.status_code != 200:
        raise ShopeeAuthError(
            f"Shopee respondeu {resp.status_code} — credencial inválida ou sem permissão."
        )

    body = resp.json()
    errors = body.get("errors")
    if errors:
        raise ShopeeCatalogError(f"Shopee retornou erros GraphQL: {errors}", errors=errors)
    if "data" not in body:
        raise ShopeeCatalogError("Resposta inesperada da Shopee (sem campo 'data').")
    return body["data"]


def _build_search_query(
    fields: tuple[str, ...],
    keyword: str | None,
    product_cat_id: int | None,
    sort_type: int,
    limit: int,
) -> str:
    args = []
    if product_cat_id:
        args.append(f"productCatId: {product_cat_id}")
    if keyword:
        safe_kw = keyword.replace('"', '\\"')
        args.append(f'keyword: "{safe_kw}"')
    args.append(f"sortType: {sort_type}")
    args.append(f"limit: {limit}")
    fields_block = "".join(f"      {f}\n" for f in fields)
    return (
        "{{"
        "  productOfferV2({0}) {{"
        "    nodes {{\n"
        "{1}"
        "    }}"
        "  }}"
        "}}"
    ).format(", ".join(args), fields_block)


async def search_products(
    app_id: str,
    secret: str,
    *,
    keyword: str | None = None,
    product_cat_id: int | None = None,
    sort_type: int = 1,
    limit: int = 20,
) -> list[dict]:
    """Busca produtos no catálogo real da Shopee. Tenta o conjunto de campos
    "rico" primeiro; se a Shopee rejeitar por schema (`Cannot query
    field...`), refaz com o conjunto mínimo garantido — nunca deixa a busca
    inteira falhar por causa de um campo best-effort."""
    rich_query = _build_search_query(
        _MINIMAL_FIELDS + _RICH_EXTRA_FIELDS, keyword, product_cat_id, sort_type, limit,
    )
    try:
        data = await _post_graphql(app_id, secret, rich_query)
    except ShopeeAuthError:
        raise
    except ShopeeCatalogError as exc:
        if not _is_unknown_field_error(exc.errors):
            raise
        minimal_query = _build_search_query(
            _MINIMAL_FIELDS, keyword, product_cat_id, sort_type, limit,
        )
        data = await _post_graphql(app_id, secret, minimal_query)

    return data.get("productOfferV2", {}).get("nodes", [])


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


async def get_category_list() -> list[dict]:
    """Árvore de categorias da Shopee (`seller.shopee.com.br`, REST simples,
    sem autenticação de afiliado) — usada como filtro de categoria no
    frontend. Mesma lógica de `apis/shopee.py::get_category_list`, sem
    dependência de `shopee_bot.*`."""
    total = 0
    items_parsed = 0
    page = 1
    categories: list[dict] = []
    seen_ids: set = set()

    while True:
        res = await _get_global_category_list(page)
        if res is None:
            raise ShopeeCatalogError("Falha ao buscar categorias da Shopee.")

        if total == 0:
            total = res["total"]

        for cat in res["global_cats"]:
            old_category_id = None
            for index, item in enumerate(cat["path"]):
                category_id = item["category_id"]
                if category_id not in seen_ids:
                    categories.append({
                        "name": item["category_name"],
                        "category_id": category_id,
                        "parent_id": old_category_id if index > 0 else None,
                    })
                    seen_ids.add(category_id)
                old_category_id = category_id
            items_parsed += 1

        if items_parsed >= total:
            break
        page += 1

    return categories
