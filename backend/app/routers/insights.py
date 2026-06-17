from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.insight import Insight
from app.schemas.insight import Insight as InsightSchema, InsightUpdate
from app.routers.accounts import get_default_user_id
from app.services.ai_engine import detect_expense_leaks

router = APIRouter(prefix="/insights", tags=["Insights"])

@router.get("/", response_model=list[InsightSchema])
def list_insights(db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    return db.query(Insight).filter(Insight.user_id == user_id).order_by(Insight.created_at.desc()).all()

@router.post("/refresh", response_model=list[InsightSchema])
def refresh_insights(db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    """
    Runs the heuristic engine to detect leaks and unused subscriptions,
    caches new warnings in the Insights database table, and returns all user insights.
    """
    leaks = detect_expense_leaks(db, user_id)
    
    # Simple deduplication: delete existing warnings of similar type before inserting fresh updates,
    # or only add if not already present.
    # To keep list clean, let's clear the old system-generated warnings
    db.query(Insight).filter(
        Insight.user_id == user_id,
        Insight.type.in_(["REPEATED_FOOD", "UNUSED_SUBSCRIPTION", "WEEKEND_OVERSPENDING"])
    ).delete(synchronize_session=False)
    
    # Add new insights
    for leak in leaks:
        db_insight = Insight(
            user_id=user_id,
            type=leak["type"],
            title=leak["title"],
            content=leak["content"],
            severity=leak["severity"],
            is_read=False
        )
        db.add(db_insight)
        
    db.commit()
    
    return db.query(Insight).filter(Insight.user_id == user_id).order_by(Insight.created_at.desc()).all()

@router.put("/{insight_id}", response_model=InsightSchema)
def update_insight(insight_id: int, update: InsightUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    db_insight = db.query(Insight).filter(Insight.id == insight_id, Insight.user_id == user_id).first()
    if not db_insight:
        raise HTTPException(status_code=404, detail="Insight not found")
        
    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_insight, key, value)
        
    db.commit()
    db.refresh(db_insight)
    return db_insight
