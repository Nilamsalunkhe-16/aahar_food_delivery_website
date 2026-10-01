from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import FoodListing
from ..schemas.food import FoodCreate, FoodOut
from ..security import current_user

router = APIRouter(prefix="/food", tags=["Food"])

@router.get("/listings", response_model=list[FoodOut])
def listings(db: Session=Depends(get_db)):
    return db.query(FoodListing).filter(
        FoodListing.status == "available",
        (FoodListing.expiry_at.is_(None)) | (FoodListing.expiry_at >= datetime.utcnow()),
    ).order_by(FoodListing.created_at.desc()).all()

@router.post("/listings", response_model=FoodOut)
def create_listing(data: FoodCreate, user=Depends(current_user), db: Session=Depends(get_db)):
    if user.role not in {"donor","admin"}: raise HTTPException(403,"Only food donors can create listings")
    expiry = datetime.utcnow() + timedelta(hours=data.expiry_hours)
    item = FoodListing(donor_id=user.id,name=data.name,food_type=data.type,quantity=data.quantity,unit=data.unit,preparation_time=data.preparation_time,expiry_at=expiry,dietary_labels=data.dietary,notes=data.notes,latitude=data.latitude if data.latitude is not None else user.latitude,longitude=data.longitude if data.longitude is not None else user.longitude,address=data.address,status="available")
    db.add(item); db.commit(); db.refresh(item)
    return item

@router.get("/mine", response_model=list[FoodOut])
def my_listings(user=Depends(current_user), db: Session=Depends(get_db)):
    return db.query(FoodListing).filter(FoodListing.donor_id == user.id).order_by(FoodListing.created_at.desc()).all()

@router.delete("/listings/{listing_id}", status_code=204)
def delete_listing(listing_id: int, user=Depends(current_user), db: Session=Depends(get_db)):
    item = db.get(FoodListing, listing_id)
    if not item:
        raise HTTPException(404, "Food listing not found")
    if item.donor_id != user.id and user.role != "admin":
        raise HTTPException(403, "Not allowed")
    if item.status != "available":
        raise HTTPException(409, "Only available listings can be removed")
    db.delete(item)
    db.commit()
