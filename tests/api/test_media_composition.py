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
