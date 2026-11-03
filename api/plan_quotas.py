"""Cotas comerciais opt-in de publicação por perfil (F4C1).

A RPC do Supabase serializa reservas na linha da conta. A API anterior da
produção segue intacta enquanto staging e main compartilham o banco.
Cada post-raiz representa exatamente uma rede; partes de thread não consomem
cotas adicionais. A reserva não equivale a confirmação de publicação externa.
"""
import logging

from fastapi import HTTPException

from .database import supabase

logger = logging.getLogger(__name__)


def reserve_post_plan_quota(
    user_id: str, profile_id: str, post_id: int, *,
    immediate: bool, days: list[int] | None = None,
    times: list[str] | None = None, reuse_existing: bool = False,
) -> None:
    """Reserva uma unidade imediata ou horários semanais antes do agendador.

    O banco confirma dono de conta/perfil/post e lê o plano de users, não
    confia em role, tier ou teto enviados pelo navegador.
    """
    try:
        supabase.rpc("reserve_post_plan_quota", {
            "p_user_id": str(user_id),
            "p_profile_id": str(profile_id),
            "p_post_id": int(post_id),
            "p_kind": "immediate" if immediate else "recurring",
            "p_days": days or [],
            "p_times": times or [],
            "p_reuse_existing": bool(reuse_existing),
        }).execute()
    except Exception as exc:
        message = str(exc)
        if "plan_immediate_quota_exceeded" in message:
            raise HTTPException(
                status_code=409,
                detail="Limite de publicações imediatas por hora deste perfil atingido.",
            ) from None
        if "plan_recurring_quota_exceeded" in message:
            raise HTTPException(
                status_code=409,
                detail="Limite de horários recorrentes por dia deste perfil atingido.",
            ) from None
        if "profile_not_owned" in message or "post_not_owned" in message:
            raise HTTPException(status_code=404, detail="Perfil ou post não encontrado.") from None
        if "plan_policy_unavailable" in message:
            raise HTTPException(
                status_code=503, detail="Política do plano indisponível. Tente novamente.",
            ) from None
        logger.error("Reserva de cota de publicação falhou: %s", type(exc).__name__)
        raise HTTPException(
            status_code=503, detail="Não foi possível verificar o limite do plano agora.",
        ) from None


def release_failed_post_plan_quota(user_id: str, profile_id: str, post_id: int) -> None:
    """Compensa somente criação não despachada; falha fechada preserva reserva.

    A RPC recusa liberar se ainda existir agenda ou ocorrência de execução.
    Não usar para falha/timeout de publicação externa (resultado pode ser unknown).
    """
    try:
        supabase.rpc("release_failed_post_plan_quota", {
            "p_user_id": str(user_id), "p_profile_id": str(profile_id),
            "p_post_id": int(post_id),
        }).execute()
    except Exception:
        logger.error("Falha de compensação da reserva do post %s", post_id, exc_info=True)
