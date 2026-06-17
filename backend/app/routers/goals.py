from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.goal import Goal
from app.schemas.goal import Goal as GoalSchema, GoalCreate, GoalUpdate
from app.routers.accounts import get_default_user_id

router = APIRouter(prefix="/goals", tags=["Goals"])

@router.post("/", response_model=GoalSchema, status_code=status.HTTP_201_CREATED)
def create_goal(goal: GoalCreate, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    db_goal = Goal(
        user_id=user_id,
        name=goal.name,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        deadline=goal.deadline,
        status=goal.status
    )
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    return db_goal

@router.get("/", response_model=list[GoalSchema])
def list_goals(db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    return db.query(Goal).filter(Goal.user_id == user_id).all()

@router.put("/{goal_id}", response_model=GoalSchema)
def update_goal(goal_id: int, goal_update: GoalUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    db_goal = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user_id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
        
    update_data = goal_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_goal, key, value)
        
    db.commit()
    db.refresh(db_goal)
    return db_goal

@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(goal_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_default_user_id)):
    db_goal = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user_id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    db.delete(db_goal)
    db.commit()
    return None
