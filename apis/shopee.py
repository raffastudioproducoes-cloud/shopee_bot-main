import requests
import hashlib
import time
import json
import re
from shopee_bot.utils import format_product_from_shopee, retry_with_backoff
from shopee_bot.returnable_thread import ReturnableThread as RT


SHOPEE_GRAPHQL_URL = "https://open-api.affiliate.shopee.com.br/graphql"


def _gen_authorization(app_id, secret, payload):
    timestamp = int(time.time())
    sign_factor = f"{app_id}{timestamp}{payload}{secret}"
    signature = hashlib.sha256(sign_factor.encode()).hexdigest()
    auth = f"SHA256 Credential={app_id}, Timestamp={
        timestamp}, Signature={signature}"
    return auth


def _query(app_id, secret, query):
    payload = json.dumps({
        "operationName": None,
        "query": query,
        "variables": None,
    })
    headers = {
        "Content-Type": "application/json",
        "Authorization": _gen_authorization(app_id, secret, payload)
    }
    res = retry_with_backoff(
        requests.post,
        SHOPEE_GRAPHQL_URL,
        payload,
        headers=headers,
        exceptions=(requests.exceptions.RequestException,)
    )
    if res.status_code == 200 and "data" in res.json():
        return res.json()["data"]
    else:
        return None


def query_products(app_id, secret, productCartId, sortType, limit=10):
    query = """
{{
  productOfferV2(productCatId: {0}, sortType: {1}, limit: {2}) {{
    nodes {{
      itemId
      offerLink
      productName
      productLink
      imageUrl
      priceMax
      priceMin
      commission
    }}
  }}
}}
""".format(productCartId, sortType, limit)
    query_res = _query(app_id, secret, query)
    if query_res:
        return query_res["productOfferV2"]["nodes"]
    else:
        return None


def _query_product(app_id, secret, product_id):
    query = """
{{
  productOfferV2(itemId: {0}) {{
    nodes {{
      itemId
      offerLink
      productName
      productLink
      imageUrl
      priceMax
      priceMin
      commission
    }}
  }}
}}
""".format(product_id)
    query_res = _query(app_id, secret, query)
    if query_res:
        return query_res["productOfferV2"]["nodes"][0]
    else:
        return None


def _query_short_link(app_id, secret, product_url, product_id):
    query = """
mutation {{
  generateShortLink (
    input: {{
      originUrl: {0}
      subIds: [{1}]
    }}
  ) {{
    shortLink
  }}
}}
""".replace("\n", "").format(json.dumps(product_url), json.dumps(product_id))
    query_res = _query(app_id, secret, query)
    if query_res:
        return query_res["generateShortLink"]["shortLink"]
    else:
        return None


def query_product(app_id, secret, product_url):
    product_id = re.findall(r"\d{5,}", product_url)[1]

    # using threads to reduce total request time
    short_link_thread = RT(
        _query_short_link,
        (app_id, secret, product_url, product_id)
    )
    short_link_thread.start()

    res_product_thread = RT(
        _query_product,
        (app_id, secret, product_id)
    )
    res_product_thread.start()

    short_link_thread.join()
    res_product_thread.join()

    short_link = short_link_thread.result
    res_product = res_product_thread.result

    product = format_product_from_shopee(res_product)
    product["commission_link"] = short_link

    return product


def query_auth_validate(app_id, secret):
    query = """
{
  productOfferV2 {
    nodes {
      itemId
    }
  }
}
""".replace("\n", "")
    query_res = _query(app_id, secret, query)
    if query_res:
        return True
    else:
        return False


def get_category_list():
    total = 0
    items_parsed = 0
    page = 1
    categories = []

    def has_category_id(category_id):
        for category in categories:
            if category["category_id"] == category_id:
                return True
        return False

    while True:
        res = _get_global_category_list(page)
        if res is None:
            return None

        if total == 0:
            total += res["total"]

        cats = res["global_cats"]
        for cat in cats:
            old_category_id = None
            for [index, item] in enumerate(cat["path"]):
                if not has_category_id(item["category_id"]):
                    new_category = {
                        "name": item["category_name"],
                        "category_id": item["category_id"],
                        "parent_id": None
                    }

                    if index > 0:
                        new_category["parent_id"] = old_category_id
                    categories.append(new_category)
                old_category_id = item["category_id"]

            items_parsed += 1
        if items_parsed >= total:
            break

        page += 1

    return categories


# https://seller.shopee.com.br/edu/category-guide
def _get_global_category_list(page, size=1000):
    url = f"""
        https://seller.shopee.com.br/help/api/v3/global_category/list/
        ?page={page}&size={size}
    """.replace("\n", "").replace(" ", "")

    res = requests.get(url)
    if res.status_code == 200 and "data" in res.json():
        return res.json()["data"]
    else:
        return None
