from shopee_bot.apis import shopee as ShopeeAPI
from shopee_bot.database import shopee_credentials, products
from shopee_bot.clogging import logger


def update_products(user_id):
    user_data = shopee_credentials.get_by_user_id(user_id)
    username = user_data["username"]
    app_id = user_data["shopee_app_id"]
    secret = user_data["shopee_secret"]
    status = user_data["shopee_status"]

    logger.info(f"Starting update_products job for {username}...")

    if not app_id or not secret or status is False:
        logger.info(
            "{0} doesn't have a Shopee API Key registered.".format(
                username
            )
        )
        return

    products_data = products.gets(user_id)

    if len(products_data) == 0:
        logger.info(f"{username} has no products to update.")
        return

    for product in products_data:
        # product id on database
        id = product["id"]

        try:
            updated_product = ShopeeAPI.query_product(
                app_id, secret, product["original_link"]
            )

            products.update(user_id, id, updated_product)
            logger.debug(
                "Product {0} from {1} updated.".format(
                    updated_product["name"],
                    username
                )
            )
        except Exception as err:
            logger.exception(f"Unexpected {err=}, {type(err)=}")

    logger.info(f"update_products job for {username} finished.")
