from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models import Lead, Activity, User


async def get_leads(db: AsyncSession, stage: str = None, industry: str = None, search: str = None) -> list[Lead]:
    q = select(Lead).order_by(Lead.created_at.desc())
    if stage:
        q = q.where(Lead.stage == stage)
    if industry:
        q = q.where(Lead.industry == industry)
    if search:
        q = q.where(Lead.name.ilike(f"%{search}%") | Lead.company.ilike(f"%{search}%"))
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_lead(db: AsyncSession, lead_id: int) -> Lead | None:
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    return result.scalar_one_or_none()


async def update_lead(db: AsyncSession, lead: Lead, data: dict) -> Lead:
    for k, v in data.items():
        if hasattr(lead, k):
            setattr(lead, k, v)
    lead.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(lead)
    return lead


async def add_activity(db: AsyncSession, lead_id: int, type: str, description: str) -> Activity:
    activity = Activity(lead_id=lead_id, type=type, description=description)
    db.add(activity)
    await db.commit()
    return activity


async def get_activities(db: AsyncSession, lead_id: int) -> list[Activity]:
    result = await db.execute(
        select(Activity).where(Activity.lead_id == lead_id).order_by(Activity.created_at.desc())
    )
    return list(result.scalars().all())


async def get_dashboard_stats(db: AsyncSession) -> dict:
    total = await db.execute(select(func.count(Lead.id)))
    pipeline_value = await db.execute(
        select(func.sum(Lead.value)).where(Lead.stage.notin_(["ganado", "perdido"]))
    )
    won = await db.execute(select(func.count(Lead.id)).where(Lead.stage == "ganado"))
    avg_score = await db.execute(
        select(func.avg(Lead.score)).where(Lead.score > 0)
    )
    stage_counts = await db.execute(
        select(Lead.stage, func.count(Lead.id)).group_by(Lead.stage)
    )
    industry_counts = await db.execute(
        select(Lead.industry, func.count(Lead.id)).group_by(Lead.industry)
    )
    total_val = total.scalar() or 0
    won_val = won.scalar() or 0
    return {
        "total_leads": total_val,
        "pipeline_value": pipeline_value.scalar() or 0,
        "conversion_rate": round((won_val / total_val * 100), 1) if total_val else 0,
        "avg_score": round(avg_score.scalar() or 0, 1),
        "by_stage": dict(stage_counts.all()),
        "by_industry": dict(industry_counts.all()),
    }


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()
