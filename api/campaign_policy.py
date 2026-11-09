"""Políticas de campanha e limites, revalidados na ativação e no executor.

Plano/papel vêm da conta; catálogo auditável da migration 072 é lido sem
cache para respeitar downgrade. Rascunhos nunca consomem vagas ativas.
A futura F4E deve revalidar e reservar vagas numa transação antes de jobs.
"""
from dataclasses import dataclass

from fastapi import HTTPException

from .database import supabase
from .campaign_schedule import (
    MAX_CAMPAIGN_CALENDAR_DAYS, count_campaign_days, plan_campaign_slots,
)


@dataclass(frozen=True)
class CampaignPolicy:
    tier: str
    is_admin: bool
    active_campaigns_limit: int | None
    campaign_days: int
    campaign_posts_per_day: int | None
    automation_enabled: bool

    @property
    def campaigns_enabled(self) -> bool:
        return self.is_admin or (
            self.tier in ("pro", "premium")
            and self.active_campaigns_limit > 0
            and self.campaign_days > 0
            and self.campaign_posts_per_day > 0
        )


def _unavailable() -> HTTPException:
    return HTTPException(status_code=503, detail="Política do plano indisponível. Tente novamente.")


def load_campaign_policy(user_id: str, profile_id: str) -> CampaignPolicy:
    """Confirma ownership mesmo com service_role e ignora claims comerciais."""
    try:
        profile = (supabase.table("profiles").select("id")
                   .eq("id", profile_id).eq("user_id", user_id)
                   .maybe_single().execute())
        if not profile or not profile.data:
            raise HTTPException(status_code=404, detail="Perfil não encontrado.")
        account = (supabase.table("users").select("access, plan_tier")
                   .eq("id", user_id).maybe_single().execute())
        if not account or not isinstance(account.data, dict):
            raise _unavailable()
        access = account.data.get("access")
        tier = account.data.get("plan_tier")
        tier = "pro" if tier == "plus" else tier
        if access not in ("USER", "ADMIN") or tier not in ("free", "pro", "premium"):
            raise _unavailable()
        if access == "ADMIN":
            return CampaignPolicy(tier, True, None, 30, None, True)
        result = (supabase.table("plan_limits").select(
            "active_campaigns_per_profile, campaign_days, campaign_posts_per_day, automation_enabled")
            .eq("tier", tier).maybe_single().execute())
        row = result.data if result else None
        fields = ("active_campaigns_per_profile", "campaign_days", "campaign_posts_per_day")
        if (not isinstance(row, dict)
                or any(type(row.get(key)) is not int or row[key] < 0 for key in fields)
                or type(row.get("automation_enabled")) is not bool):
            raise _unavailable()
        return CampaignPolicy(
            tier, False, row["active_campaigns_per_profile"],
            min(row["campaign_days"], 30), row["campaign_posts_per_day"],
            tier == "premium" and row["automation_enabled"],
        )
    except HTTPException:
        raise
    except Exception:
        # Não expor erro do banco nem assumir Free/Premium/uso zero na falha.
        raise _unavailable() from None


def require_campaign_access(policy: CampaignPolicy) -> None:
    if not policy.campaigns_enabled:
        raise HTTPException(status_code=403, detail="Campanhas disponíveis nos planos Pro e Premium.")


def validate_campaign_plan_schedule(policy: CampaignPolicy, schedule) -> None:
    """Valida dias efetivos de publicação e mantém teto físico do calendário."""
    require_campaign_access(policy)
    if schedule is None:
        return
    calendar_days = (schedule.end_date - schedule.start_date).days + 1
    if calendar_days < 1 or calendar_days > MAX_CAMPAIGN_CALENDAR_DAYS:
        raise HTTPException(
            status_code=422, detail="O intervalo deve ter de 1 a 210 dias corridos inclusivos.",
        )
    try:
        active_days = count_campaign_days(schedule.start_date, schedule.end_date, schedule.weekdays)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if active_days < 1:
        raise HTTPException(status_code=422, detail="Nenhum dia selecionado ocorre no período informado.")
    if active_days > 30:
        raise HTTPException(status_code=422, detail="O limite absoluto é de 30 dias efetivos de publicação.")
    if active_days > policy.campaign_days:
        raise HTTPException(
            status_code=403,
            detail=f"Seu plano permite até {policy.campaign_days} dias de publicação nos dias da semana selecionados.",
        )
    if not policy.is_admin and schedule.posts_per_day > policy.campaign_posts_per_day:
        raise HTTPException(
            status_code=403,
            detail=f"Seu plano permite até {policy.campaign_posts_per_day} publicações por dia de campanha.",
        )


def validate_campaign_network_volume(policy: CampaignPolicy, schedule, items) -> None:
    """Cada rede selecionada conta uma publicação; não confundir slot com envio."""
    if schedule is None or policy.is_admin:
        return
    slots = plan_campaign_slots(
        start_date=schedule.start_date, end_date=schedule.end_date,
        weekdays=schedule.weekdays, start_time=schedule.start_time,
        end_time=schedule.end_time, posts_per_day=schedule.posts_per_day,
        item_ids=schedule.item_ids, timezone="America/Sao_Paulo",
    )
    networks = {item.product_id: len(item.networks) for item in items}
    counts = {}
    for slot in slots:
        day = slot.local_at.date()
        counts[day] = counts.get(day, 0) + networks[slot.item_id]
        if counts[day] > policy.campaign_posts_per_day:
            raise HTTPException(
                status_code=403,
                detail=f"Seu plano permite até {policy.campaign_posts_per_day} publicações por dia de campanha; cada rede conta uma.",
            )


def require_automation_access(policy: CampaignPolicy) -> None:
    """Guarda reutilizável para a entrada futura; não cria automação operacional."""
    if not policy.automation_enabled:
        raise HTTPException(status_code=403, detail="Automação disponível no plano Premium.")


def campaign_limits_response(policy: CampaignPolicy, profile_id: str) -> dict:
    """Failures in commercial entitlement/usage readings fail closed."""
    from datetime import datetime, timezone
    paid_through = None
    eligible = policy.is_admin
    active_count = None
    try:
        account = (supabase.table("profiles").select("user_id")
                   .eq("id",profile_id).single().execute()).data
        user = (supabase.table("users")
                .select("campaign_paid_through,campaign_pending_tier,campaign_tier_effective_at")
                .eq("id",account["user_id"]).single().execute()).data
        paid_through = user.get("campaign_paid_through")
        if paid_through and not policy.is_admin:
            paid = datetime.fromisoformat(paid_through.replace("Z","+00:00"))
            eligible = paid > datetime.now(timezone.utc) and policy.campaigns_enabled
        count = (supabase.table("campaign_reservations_f4e")
                 .select("id",count="exact",head=True)
                 .eq("profile_id",profile_id).eq("user_id",account["user_id"])
                 .eq("status","reserved_no_dispatch")
                 .in_("lifecycle",["preparing","active","paused"]).execute())
        active_count = count.count
    except Exception:
        eligible = policy.is_admin
        active_count = None
    quota_available = policy.is_admin or (
        policy.active_campaigns_limit is not None and active_count is not None
        and active_count < policy.active_campaigns_limit
    )
    activation_available = eligible and active_count is not None and quota_available
    if active_count is None:
        message = "Não foi possível consultar a capacidade de campanhas ativas."
    elif not eligible:
        message = "Ativação exige período pago confirmado e capacidade disponível."
    elif not quota_available:
        message = "Limite de campanhas ativas do plano atingido."
    else:
        message = "Ativação permitida, sujeita à revisão de mídia, OAuth e cotas."
    return {
        "profile_id": profile_id,
        "plan_tier": policy.tier,
        "is_admin": policy.is_admin,
        "campaigns_enabled": policy.campaigns_enabled,
        "active_campaigns_limit": policy.active_campaigns_limit,
        "active_campaigns_count": active_count,
        "active_campaigns_usage_status": "available" if active_count is not None else "unavailable",
        "campaign_days": policy.campaign_days,
        "campaign_posts_per_day": policy.campaign_posts_per_day,
        "absolute_campaign_days": 30,
        "automation_entitled": policy.automation_enabled,
        "automation_available": eligible and policy.automation_enabled,
        "activation_available": activation_available,
        "campaign_paid_through": paid_through,
        "message": message,
    }
