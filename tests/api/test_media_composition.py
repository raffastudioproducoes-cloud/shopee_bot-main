from api.media_composition import plan_network_composition


def _image(media_id: int, name: str = "foto.jpg") -> dict:
    return {"id": media_id, "file_name": name, "size": 1024}


def test_five_images_for_x_keep_only_the_first_deliverable_image():
    medias = [_image(index) for index in range(1, 6)]

    plan = plan_network_composition("x", ["copy"], medias)

    assert plan.mode == "single_image"
    assert plan.media_ids == [1]
    assert [d["id"] for d in plan.dropped] == [2, 3, 4, 5]
    assert [media["id"] for media in medias] == [1, 2, 3, 4, 5]


def test_x_blocks_invalid_text_instead_of_falling_back_from_invalid_media():
    plan = plan_network_composition("x", ["x" * 281], [_image(index) for index in range(1, 6)])

    assert plan.mode == "blocked"
    assert "texto máx. 280" in plan.blocked_reason


def test_x_single_image_is_delivered():
    plan = plan_network_composition("x", ["copy"], [_image(1)])

    assert plan.mode == "single_image"
    assert plan.media_ids == [1]


def test_x_keeps_first_image_when_carousel_is_not_delivered():
    plan = plan_network_composition("x", ["copy"], [_image(1), _image(2)])

    assert plan.mode == "single_image"
    assert plan.media_ids == [1]
    assert plan.dropped[0]["id"] == 2 and plan.dropped[0]["reason"]


def test_instagram_carousel_keeps_the_original_order_and_allows_mixed_media():
    plan = plan_network_composition("instagram", ["copy"], [_image(3), _image(1, "clipe.mp4")])

    assert plan.mode == "carousel"
    assert plan.media_ids == [3, 1]


def test_instagram_truncates_at_ten_medias_in_user_order():
    plan = plan_network_composition("instagram", ["copy"], [_image(i) for i in range(1, 12)])

    assert plan.mode == "carousel"
    assert plan.media_ids == list(range(1, 11))
    assert [d["id"] for d in plan.dropped] == [11]


def test_tiktok_photo_only_is_blocked_when_text_only_is_not_supported():
    plan = plan_network_composition("tiktok", ["copy"], [_image(1)])

    assert plan.mode == "blocked"
    assert plan.media_ids == []
    assert plan.blocked_reason


def test_threads_images_become_a_carousel_in_the_original_order():
    plan = plan_network_composition("threads", ["copy"], [_image(3), _image(1)])

    assert plan.mode == "carousel"
    assert plan.media_ids == [3, 1]
    assert plan.warnings == []


def test_instagram_without_media_or_product_is_blocked():
    plan = plan_network_composition("instagram", ["copy"], [])

    assert plan.mode == "blocked"
    assert "exige imagem" in plan.blocked_reason


def test_facebook_images_become_an_album_in_the_original_order():
    plan = plan_network_composition("facebook", ["copy"], [_image(3), _image(1)])

    assert plan.mode == "carousel"
    assert plan.media_ids == [3, 1]


def test_facebook_album_prefers_images_and_drops_gif_or_video():
    gif = plan_network_composition("facebook", ["copy"], [_image(1), _image(2, "a.gif")])
    video = plan_network_composition("facebook", ["copy"], [_image(1), _image(2, "a.mp4")])

    assert gif.mode == "single_image" and gif.media_ids == [1]
    assert video.mode == "single_image" and video.media_ids == [1]
    assert video.dropped[0]["id"] == 2


def test_facebook_single_video_is_delivered():
    plan = plan_network_composition("facebook", ["copy"], [_image(4, "clipe.mp4")])

    assert plan.mode == "video"
    assert plan.media_ids == [4]


def test_facebook_two_videos_keep_only_the_first():
    plan = plan_network_composition(
        "facebook", ["copy"], [_image(1, "a.mp4"), _image(2, "b.mp4")]
    )

    assert plan.mode == "video"
    assert plan.media_ids == [1]


def test_instagram_single_video_is_delivered():
    plan = plan_network_composition("instagram", ["copy"], [_image(4, "clipe.mp4")])

    assert plan.mode == "video"
    assert plan.media_ids == [4]


def test_facebook_without_images_sends_the_video():
    plan = plan_network_composition("facebook", ["copy"], [_image(1, "a.mp4"), _image(2, "b.gif")])

    assert plan.mode == "video" and plan.media_ids == [1]


def test_tiktok_drops_photos_and_keeps_the_video():
    plan = plan_network_composition(
        "tiktok", ["copy"], [_image(1), _image(2, "a.mp4"), _image(3, "b.png")]
    )

    assert plan.mode == "video"
    assert plan.media_ids == [2]
    assert [d["id"] for d in plan.dropped] == [1, 3]


def test_unaccepted_extension_is_dropped_not_blocking_the_network():
    plan = plan_network_composition("instagram", ["copy"], [_image(1), _image(2, "a.webp")])

    assert plan.mode == "single_image"
    assert plan.media_ids == [1]
    assert "formato" in plan.dropped[0]["reason"]


def test_oversized_file_is_dropped():
    big = {"id": 2, "file_name": "grande.jpg", "size": 9 * 1024 * 1024}
    plan = plan_network_composition("instagram", ["copy"], [_image(1), big])

    assert plan.media_ids == [1]
    assert "tamanho" in plan.dropped[0]["reason"]


def test_text_only_network_with_nothing_usable_becomes_text_only_with_reason():
    plan = plan_network_composition("facebook", ["copy"], [_image(1, "a.webp")])

    assert plan.mode == "text_only"
    assert plan.media_ids == []
    assert plan.warnings


def test_network_without_text_only_is_blocked_when_nothing_serves():
    plan = plan_network_composition("instagram", ["copy"], [_image(1, "a.webp")])

    assert plan.mode == "blocked"
    assert plan.blocked_reason


def test_threads_keeps_twenty_and_drops_the_extras():
    plan = plan_network_composition("threads", ["copy"], [_image(i) for i in range(1, 23)])

    assert plan.mode == "carousel"
    assert plan.media_ids == list(range(1, 21))
    assert [d["id"] for d in plan.dropped] == [21, 22]
