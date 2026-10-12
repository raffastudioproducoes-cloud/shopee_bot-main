from api.media_composition import plan_network_composition


def _image(media_id: int, name: str = "foto.jpg") -> dict:
    return {"id": media_id, "file_name": name, "size": 1024}


def test_five_images_for_x_falls_back_without_mutating_ids():
    medias = [_image(index) for index in range(1, 6)]

    plan = plan_network_composition("x", ["copy"], medias)

    assert plan.mode == "text_only"
    assert plan.media_ids == []
    assert plan.text_variant == ["copy"]
    assert "máx. 4" in plan.warnings[0]
    assert [media["id"] for media in medias] == [1, 2, 3, 4, 5]


def test_x_blocks_invalid_text_instead_of_falling_back_from_invalid_media():
    plan = plan_network_composition("x", ["x" * 281], [_image(index) for index in range(1, 6)])

    assert plan.mode == "blocked"
    assert "texto máx. 280" in plan.blocked_reason


def test_x_falls_back_to_delivered_text_only_when_image_mode_is_not_delivered():
    plan = plan_network_composition("x", ["copy"], [_image(1)])

    assert plan.mode == "text_only"
    assert "ainda não é entregue" in plan.warnings[0]


def test_instagram_carousel_keeps_the_original_order_and_allows_mixed_media():
    plan = plan_network_composition("instagram", ["copy"], [_image(3), _image(1, "clipe.mp4")])

    assert plan.mode == "carousel"
    assert plan.media_ids == [3, 1]


def test_instagram_blocks_more_than_ten_medias_without_dropping_files():
    plan = plan_network_composition("instagram", ["copy"], [_image(i) for i in range(1, 12)])

    assert plan.mode == "blocked"
    assert "máx. 10" in plan.blocked_reason


def test_tiktok_photo_is_blocked_when_text_only_is_not_supported():
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


def test_facebook_album_does_not_mix_images_with_gif_or_video():
    gif = plan_network_composition("facebook", ["copy"], [_image(1), _image(2, "a.gif")])
    video = plan_network_composition("facebook", ["copy"], [_image(1), _image(2, "a.mp4")])

    assert gif.mode == "text_only" and gif.media_ids == []
    assert video.mode == "text_only" and video.media_ids == []


def test_facebook_single_video_is_delivered():
    plan = plan_network_composition("facebook", ["copy"], [_image(4, "clipe.mp4")])

    assert plan.mode == "video"
    assert plan.media_ids == [4]


def test_facebook_two_videos_are_not_published_as_an_album():
    plan = plan_network_composition(
        "facebook", ["copy"], [_image(1, "a.mp4"), _image(2, "b.mp4")]
    )

    assert plan.mode == "text_only"
    assert plan.media_ids == []


def test_instagram_single_video_is_delivered():
    plan = plan_network_composition("instagram", ["copy"], [_image(4, "clipe.mp4")])

    assert plan.mode == "video"
    assert plan.media_ids == [4]
