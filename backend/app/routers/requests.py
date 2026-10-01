from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import FoodRequest, FoodListing, Notification, Delivery, User
from ..security import current_user, require_roles
from pydantic import BaseModel, Field

router = APIRouter(prefix="/requests", tags=["Food Requests"])

class RequestCreate(BaseModel):
    listing_id: int
    requested_quantity: float = Field(gt=0)

@router.post("")
def create_request(data: RequestCreate, user=Depends(require_roles("ngo","community_worker","admin")), db: Session=Depends(get_db)):
    listing = db.get(FoodListing, data.listing_id)
    if not listing or listing.status != "available":
        raise HTTPException(404, "Food listing is not available")
    if listing.donor_id == user.id:
        raise HTTPException(400, "You cannot request your own listing")
    if data.requested_quantity > float(listing.quantity):
        raise HTTPException(400, "Requested quantity exceeds the available amount")
    req = FoodRequest(listing_id=listing.id, requester_id=user.id, requested_quantity=data.requested_quantity)
    listing.status = "pending"
    db.add(req)
    db.add(Notification(user_id=listing.donor_id, title="New food request", message=f"{user.full_name} requested {data.requested_quantity} {listing.unit} of {listing.name}", channel="in_app"))
    db.commit(); db.refresh(req)
    return req

@router.patch("/{request_id}")
def update_request(request_id: int, status: str, user=Depends(current_user), db: Session=Depends(get_db)):
    req = db.get(FoodRequest, request_id)
    if not req: raise HTTPException(404, "Request not found")
    listing = db.get(FoodListing, req.listing_id)
    if not listing:
        raise HTTPException(404, "Food listing not found")
    if user.id not in {req.requester_id, listing.donor_id} and user.role != "admin":
        raise HTTPException(403, "Not allowed")
    if status not in {"accepted","rejected","cancelled"}:
        raise HTTPException(400, "Invalid status")
    if req.status != "pending":
        raise HTTPException(409, "Only pending requests can be updated")
    if status in {"accepted", "rejected"} and user.id != listing.donor_id and user.role != "admin":
        raise HTTPException(403, "Only the listing donor or an admin can decide a request")
    if status == "cancelled" and user.id != req.requester_id and user.role != "admin":
        raise HTTPException(403, "Only the requester or an admin can cancel a request")
    req.status = status
    if status == "accepted":
        listing.status = "accepted"
        if not db.query(Delivery).filter(Delivery.request_id == req.id).first():
            requester = db.get(User, req.requester_id)
            db.add(Delivery(
                listing_id=listing.id,
                request_id=req.id,
                donor_lat=listing.latitude,
                donor_lng=listing.longitude,
                destination_lat=requester.latitude,
                destination_lng=requester.longitude,
                status="assigned",
            ))
    if status in {"rejected","cancelled"}: listing.status = "available"
    db.add(Notification(user_id=req.requester_id, title="Food request updated", message=f"Your request for {listing.name} is {status}.", channel="in_app"))
    db.commit()
    return {"status": status}

@router.get("/mine")
def my_requests(user=Depends(current_user), db: Session=Depends(get_db)):
    rows = db.query(FoodRequest, FoodListing).join(
        FoodListing, FoodRequest.listing_id == FoodListing.id
    ).filter(FoodRequest.requester_id == user.id).order_by(FoodRequest.created_at.desc()).all()
    return [
        {
            "id": request.id,
            "listing_id": request.listing_id,
            "listing_name": listing.name,
            "requested_quantity": float(request.requested_quantity),
            "unit": listing.unit,
            "status": request.status,
            "created_at": request.created_at,
        }
        for request, listing in rows
    ]

@router.get("/inbox")
def request_inbox(user=Depends(current_user), db: Session=Depends(get_db)):
    if user.role not in {"donor", "admin"}:
        raise HTTPException(403, "Only donors and admins can view the request inbox")
    query = db.query(FoodRequest, FoodListing).join(FoodListing, FoodRequest.listing_id == FoodListing.id)
    if user.role != "admin":
        query = query.filter(FoodListing.donor_id == user.id)
    return [
        {
            "id": request.id,
            "listing_id": request.listing_id,
            "listing_name": listing.name,
            "requester_id": request.requester_id,
            "requested_quantity": float(request.requested_quantity),
            "unit": listing.unit,
            "status": request.status,
            "created_at": request.created_at,
        }
        for request, listing in query.order_by(FoodRequest.created_at.desc()).all()
    ]
