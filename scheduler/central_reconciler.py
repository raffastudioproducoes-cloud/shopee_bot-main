"""Espelha apenas agendas explicitamente centrais para o APScheduler de produção.

Uma agenda legacy, incluindo as cinco cron de staging observadas em
02/11/2026, nunca é importada. O job persistido tem prefixo distinto; 
a identidade de publicação/claim continua sendo o UUID de schedulers.
"""

from shopee_bot.database import schedulers
from shopee_bot.utils.timezones import timezone_or_default

PREFIX = "central:"
MISFIRE_SECONDS = 3600


def _mirror_id(schedule_id):
    return f"{PREFIX}{schedule_id}"


def reconcile(scheduler, run_central):
    """Sincroniza criação/edição/cancelamento de futuras ocorrências.

    Chamado somente no executor central após validar o feature gate.
    Cancelem-se mirrors órfãos; preservam-se todas as agendas legacy.
    """
    wanted = {}
    for record in schedulers.list_central_dispatch_jobs():
        original_id = str(record["id"])
        mirror_id = _mirror_id(original_id)
        marker = f"central:r{record['dispatch_revision']}"
        wanted[mirror_id] = marker
        old = scheduler.get_job(mirror_id, jobstore="default")
        if old is not None and old.name == marker:
            continue

        kwargs = {
            "id": mirror_id,
            "name": marker,
            "jobstore": "default",
            "replace_existing": True,
            "func": run_central,
            "args": (original_id,),
            "misfire_grace_time": MISFIRE_SECONDS,
        }
        if record["trigger"] == "cron":
            clock = record["time"]
            days = record.get("days_of_week") or [record["day_of_week"]]
            if clock is None or not days:
                raise ValueError("Agenda central cron sem horário/dias")
            kwargs.update(
                trigger="cron", minute=clock.minute, hour=clock.hour,
                day_of_week=",".join(str(day) for day in days),
                start_date=record.get("start_date"),
                timezone=timezone_or_default(record.get("timezone")),
            )
        elif record["trigger"] == "date":
            if record.get("run_date") is None:
                raise ValueError("Agenda central date sem run_date")
            kwargs.update(trigger="date", run_date=record["run_date"])
        else:
            raise ValueError("Trigger central não suportado")
        scheduler.add_job(**kwargs)

    # Jobs antigos completados/cancelados saem do espelho persistido.
    # Só tocar IDs com prefixo central; não remover legacy.
    for existing in scheduler.get_jobs(jobstore="default"):
        if existing.id.startswith(PREFIX) and existing.id not in wanted:
            scheduler.remove_job(existing.id)
