"""Planejamento determinístico de slots de campanhas, sem efeitos externos.

A criação/publicação de jobs, políticas anti-spam por rede, permissões e
idempotência são responsabilidades de camadas separadas. Este módulo
apenas distribui um produto por ocorrência no calendário local.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone as utc_timezone
from typing import Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class CampaignSlot:
    """Ocorrência prevista; índice estável dentro de uma sequência gerada."""

    occurrence_index: int
    item_id: int
    local_at: datetime
    utc_at: datetime


def plan_campaign_slots(
    start_date: date,
    end_date: date,
    weekdays: Sequence[int],
    start_time: time,
    end_time: time,
    posts_per_day: int,
    item_ids: Sequence[int],
    timezone: str = "America/Sao_Paulo",
    start_occurrence_index: int = 0,
) -> list[CampaignSlot]:
    """Gera slots inclusivos, rotacionando um item por horário.

    Dias da semana seguem Python: segunda=0 ... domingo=6.
    Distribui 1 a 15 publicações por dia uniformemente na janela local;
    uma publicação usa o horário inicial. Isso é prévia, não envio real.
    O máximo absoluto são 30 dias corridos INCLUSIVOS; limites menores
    por plano e intervalos mínimos de cada rede são validados pelo serviço.
    `start_occurrence_index` permite continuar uma sequência sem reiniciá-la
    depois de uma revisão que afeta somente ocorrências futuras.
    """
    if not isinstance(start_date, date) or not isinstance(end_date, date):
        raise ValueError("Datas de início e fim inválidas.")
    total_days = (end_date - start_date).days + 1
    if total_days < 1:
        raise ValueError("A data final não pode anteceder a inicial.")
    if total_days > 30:
        raise ValueError("O período não pode ultrapassar 30 dias inclusivos.")
    if not weekdays:
        raise ValueError("Selecione ao menos um dos dias da semana.")
    if any(type(day) is not int or not 0 <= day <= 6 for day in weekdays):
        raise ValueError("Os dias da semana devem estar entre 0 e 6.")
    if not item_ids:
        raise ValueError("Selecione ao menos um produto da lista.")
    if (
        type(posts_per_day) is not int
        or not 1 <= posts_per_day <= 15
        or type(start_occurrence_index) is not int
        or start_occurrence_index < 0
    ):
        raise ValueError("Postagens por dia devem estar entre 1 e 15; índice positivo.")
    if not isinstance(start_time, time) or not isinstance(end_time, time):
        raise ValueError("Informe horários de início e fim válidos.")
    if start_time.tzinfo is not None or end_time.tzinfo is not None:
        raise ValueError("Informe horários locais sem fuso; o fuso é configurado separadamente.")
    if end_time < start_time:
        raise ValueError("A hora final deve ser posterior ou igual à inicial.")
    window_minutes = (datetime.combine(date.min, end_time) - datetime.combine(date.min, start_time)).total_seconds() / 60
    if posts_per_day > 1 and window_minutes < posts_per_day - 1:
        raise ValueError("A janela diária é curta para essa quantidade; amplie o horário ou reduza as postagens por dia.")
    try:
        local_timezone = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, TypeError, ValueError) as exc:
        raise ValueError("Fuso horário inválido.") from exc

    result: list[CampaignSlot] = []
    selected_weekdays = set(weekdays)
    current_day = start_date
    daily_offsets = [timedelta(minutes=round(window_minutes * index / (posts_per_day - 1)))
                     for index in range(posts_per_day)] if posts_per_day > 1 else [timedelta(0)]

    while current_day <= end_date:
        if current_day.weekday() in selected_weekdays:
            for offset in daily_offsets:
                current = datetime.combine(current_day, start_time) + offset
                local_at = current.replace(tzinfo=local_timezone, fold=0)
                utc_at = local_at.astimezone(utc_timezone.utc)

                # Em dias históricos de mudança de horário de verão uma
                # hora pode não existir ou pode ocorrer duas vezes. Falhar
                # explicitamente evita disparos duplicados/omitidos.
                alternative = current.replace(tzinfo=local_timezone, fold=1)
                if (
                    local_at.utcoffset() != alternative.utcoffset()
                    or utc_at.astimezone(local_timezone).replace(tzinfo=None) != current
                ):
                    raise ValueError("Horário ambíguo ou inexistente no fuso configurado.")

                occurrence_index = start_occurrence_index + len(result)
                item_id = item_ids[occurrence_index % len(item_ids)]
                result.append(
                    CampaignSlot(
                        occurrence_index=occurrence_index,
                        item_id=item_id,
                        local_at=local_at,
                        utc_at=utc_at,
                    )
                )
        current_day += timedelta(days=1)

    return result
