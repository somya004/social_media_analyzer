from app.models.schemas import MediaMetadata


def compute_engagement_rate(meta: MediaMetadata) -> float | None:
    """Engagement rate = (likes + comments) / views"""
    if not meta.views or meta.views == 0:
        return None
    interactions = (meta.likes or 0) + (meta.comments or 0)
    return round(interactions / meta.views * 100, 4)


def summarize(meta: MediaMetadata) -> dict:
    return {
        "title": meta.title,
        "author": meta.author,
        "views": meta.views,
        "likes": meta.likes,
        "comments": meta.comments,
        "engagement_rate_pct": compute_engagement_rate(meta),
        "duration_seconds": meta.duration,
    }
