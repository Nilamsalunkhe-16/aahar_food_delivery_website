from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import Notification
from ..security import current_user

router=APIRouter(prefix="/notifications",tags=["Notifications"])

@router.get("")
def notifications(user=Depends(current_user),db:Session=Depends(get_db)):
    return db.query(Notification).filter(Notification.user_id==user.id).order_by(Notification.created_at.desc()).limit(50).all()

@router.patch("/{notification_id}/read")
def mark_read(notification_id: int, user=Depends(current_user), db: Session=Depends(get_db)):
    item = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user.id,
    ).first()
    if not item:
        raise HTTPException(404, "Notification not found")
    item.is_read = True
    db.commit()
    return {"id": item.id, "is_read": item.is_read}

@router.post("/read-all")
def mark_all_read(user=Depends(current_user), db: Session=Depends(get_db)):
    db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.is_read.is_(False),
    ).update({Notification.is_read: True}, synchronize_session=False)
    db.commit()
    return {"status": "ok"}
