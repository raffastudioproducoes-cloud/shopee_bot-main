from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..database import supabase
from ..auth import get_current_user_id

router = APIRouter(prefix="/panel", tags=["panel"])


class PanelMetrics(BaseModel):
    products_count: int
    posts_count: int
    product_lists_count: int
    recent_posts: list[dict]
    recent_activities: list[dict]


@router.get("/", response_model=PanelMetrics)
async def panel_home(user_id: int = Depends(get_current_user_id)):
    sb = supabase()

    # Contagens
    products_res = sb.table("products").select("id", count="exact").eq("user_id", user_id).execute()
    posts_res = sb.table("posts").select("id", count="exact").eq("user_id", user_id).execute()
    lists_res = sb.table("product_lists").select("id", count="exact").eq("user_id", user_id).execute()

    products_count = products_res.count or 0
    posts_count = posts_res.count or 0
    product_lists_count = lists_res.count or 0

    # Posts recentes (últimos 5)
    recent_posts_res = (
        sb.table("posts")
        .select("id, text, scheduler_id, run_date, time, children, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )
    recent_posts = []
    for p in (recent_posts_res.data or []):
        scheduler_id = p.get("scheduler_id")
        has_scheduler = bool(scheduler_id)
        recent_posts.append({
            "id": p["id"],
            "text": p.get("text") or "(sem texto)",
            "has_scheduler": has_scheduler,
            "run_date": p.get("run_date"),
            "time": p.get("time"),
            "children": p.get("children"),
            "status": "AGENDADO" if has_scheduler else "RASCUNHO",
        })

    # Atividades recentes (últimas 10)
    activities_res = (
        sb.table("activities")
        .select("id, metadata, created_at, activity_type_id")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )
    recent_activities = []
    for a in (activities_res.data or []):
        meta = a.get("metadata")
        activity_type_id = a.get("activity_type_id")
        recent_activities.append({
            "id": a["id"],
            "metadata": meta,
            "created_at": a["created_at"],
            "activity_type_id": activity_type_id,
        })

    return PanelMetrics(
        products_count=products_count,
        posts_count=posts_count,
        product_lists_count=product_lists_count,
        recent_posts=recent_posts,
        recent_activities=recent_activities,
    )
