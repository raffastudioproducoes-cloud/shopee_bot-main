from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from shopee_bot.database import query_db
from shopee_bot.database.activities import query_activities_paginated

activities_bp = Blueprint("activities", __name__)


@activities_bp.get("/activities")
@login_required
def index():
    # Activities Log
    count_query = "SELECT COUNT(*) FROM activities WHERE user_id = %s"
    count = query_db(count_query, (current_user.id, ), True)["count"]

    cursor = request.args.get("cursor")
    limit = int(request.args.get("limit", 20))

    activities, next_cursor = query_activities_paginated(
        current_user.id,
        cursor,
        limit
    )

    return render_template(
        "activities/index.html",
        activities=activities,
        count=count,
        cursor=cursor,
        limit=limit,
        next_cursor=next_cursor,
    )
