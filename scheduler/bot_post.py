from shopee_bot.apis import threads as ThreadsAPI
from shopee_bot.apis.cloudinary import cloudinary as CloudinaryAPI
from shopee_bot.clogging import logger
from shopee_bot.database import schedulers, threads_credentials, posts


def _carousel_post(user_data, post, reply_to_id=None):
    threads_user_id = user_data["threads_user_id"]
    threads_access_token = user_data["threads_access_token"]

    medias = list()
    media_ids = list()
    for media in post["medias"]:
        res = None
        if media["type"] == "IMAGE":
            res = CloudinaryAPI.uploader.upload(
                media["file_path"],
                format="jpg"
            )
        else:
            res = CloudinaryAPI.uploader.upload(
                media["file_path"],
                resource_type="video"
            )

        medias.append({
            "type": media["type"],
            "url": res["url"]
        })
        media_ids.append(res["public_id"])

    item_id = ThreadsAPI.make_carousel_post(
        threads_user_id,
        threads_access_token,
        post["text"],
        medias,
        reply_to_id
    )

    for media_id in media_ids:
        CloudinaryAPI.uploader.destroy(media_id)

    return item_id


def _media_post(user_data, post, reply_to_id=None):
    threads_user_id = user_data["threads_user_id"]
    threads_access_token = user_data["threads_access_token"]

    res = None
    item_id = None
    media = post["medias"][0]
    if media["type"] == "IMAGE":
        res = CloudinaryAPI.uploader.upload(
            media["file_path"],
            format="jpg"
        )

        item_id = ThreadsAPI.make_post(
            threads_user_id,
            threads_access_token,
            post["text"],
            media_type="IMAGE",
            image_url=res["url"],
            reply_to_id=reply_to_id
        )
    else:
        res = CloudinaryAPI.uploader.upload(
            media["file_path"],
            resource_type="video"
        )

        item_id = ThreadsAPI.make_post(
            threads_user_id,
            threads_access_token,
            post["text"],
            media_type="VIDEO",
            video_url=res["url"],
            reply_to_id=reply_to_id
        )

    CloudinaryAPI.uploader.destroy(res["public_id"])
    return item_id


def _text_post(user_data, post, reply_to_id=None):
    threads_user_id = user_data["threads_user_id"]
    threads_access_token = user_data["threads_access_token"]

    return ThreadsAPI.make_post(
        threads_user_id,
        threads_access_token,
        post["text"],
        reply_to_id=reply_to_id
    )


def bot_post(job_id):
    logger.info(f"Running job #{job_id}...")

    job_data = schedulers.get_by_id(job_id)
    user_id = job_data["user_id"]
    post_id = job_data["post_id"]

    user_data = threads_credentials.get_by_user_id(user_id)
    username = user_data["username"]
    logger.info(f"job #{job_id} is {username}'s.")

    last_post_id = None
    post_data = posts.get(user_id, post_id)
    for post in post_data:
        if len(post["medias"]) > 1:
            last_post_id = _carousel_post(user_data, post, last_post_id)

        elif len(post["medias"]) > 0:
            last_post_id = _media_post(user_data, post, last_post_id)

        else:
            last_post_id = _text_post(user_data, post, last_post_id)

    logger.info(f"bot_post job #{job_id} for {username} finished.")
