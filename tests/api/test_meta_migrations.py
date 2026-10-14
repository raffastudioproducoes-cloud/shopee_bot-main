from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_050_drops_legacy_unique_data_deletion_hash_index():
    sql = (
        ROOT
        / "database"
        / "migrations"
        / "050_add_fb_user_id_to_meta_credentials.sql"
    ).read_text(encoding="utf-8").lower()

    assert "drop index if exists public.uq_data_deletion_requests_provider_hash" in sql
    assert "delete from public.data_deletion_requests" not in sql
    assert "truncate public.data_deletion_requests" not in sql
