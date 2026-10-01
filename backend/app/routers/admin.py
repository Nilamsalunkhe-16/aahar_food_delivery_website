from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import User, FoodListing, FoodRequest, Delivery, ImpactMetric
from ..schemas.auth import UserOut
from ..security import require_roles

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/overview")
def overview(user=Depends(require_roles("admin")), db: Session=Depends(get_db)):
    return {
        "users": db.query(User).count(),
        "food_listings": db.query(FoodListing).count(),
        "requests": db.query(FoodRequest).count(),
        "deliveries": db.query(Delivery).count(),
        "food_rescued_kg": float(sum((x.food_rescued_kg or 0) for x in db.query(ImpactMetric).all()))
    }

@router.get("/users", response_model=list[UserOut])
def users(user=Depends(require_roles("admin")), db: Session=Depends(get_db)):
    return db.query(User).order_by(User.created_at.desc()).limit(200).all()

@router.patch("/users/{user_id}/verify")
def verify_user(user_id: int, verified: bool, user=Depends(require_roles("admin")), db: Session=Depends(get_db)):
    target = db.get(User, user_id)
    if not target: raise HTTPException(404, "User not found")
    target.is_verified = verified
    db.commit()
    return {"id": target.id, "is_verified": target.is_verified}
