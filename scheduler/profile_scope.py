"""Guardas de isolamento para jobs que publicam em redes sociais."""


def require_profile_id(job_data):
    """Impede que jobs antigos escolham credenciais de outro perfil."""
    profile_id = job_data.get("profile_id")
    if not profile_id:
        raise RuntimeError("Job sem profile_id; recrie a publicacao pelo perfil ativo.")
    return profile_id
