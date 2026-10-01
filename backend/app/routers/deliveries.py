from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..database import get_db
from ..models.models import Delivery, DeliveryLocation, FoodListing, FoodRequest, Notification
from ..security import current_user

router = APIRouter(prefix="/deliveries", tags=["Deliveries"])

class LocationIn(BaseModel):
    latitude: float
    longitude: float

@router.get("")
def deliveries(user=Depends(current_user), db: Session=Depends(get_db)):
    q = db.query(Delivery, FoodListing.name).join(FoodListing, Delivery.listing_id == FoodListing.id)
    if user.role == "volunteer":
        q = q.filter((Delivery.volunteer_id == user.id) | (Delivery.volunteer_id.is_(None)))
    elif user.role != "admin":
        q = q.join(FoodRequest, Delivery.request_id == FoodRequest.id).filter(
            (FoodListing.donor_id == user.id) | (FoodRequest.requester_id == user.id)
        )
    return [
        {
            "id": delivery.id,
            "listing_id": delivery.listing_id,
            "listing_name": listing_name,
            "request_id": delivery.request_id,
            "volunteer_id": delivery.volunteer_id,
            "donor_lat": delivery.donor_lat,
            "donor_lng": delivery.donor_lng,
            "destination_lat": delivery.destination_lat,
            "destination_lng": delivery.destination_lng,
            "vehicle_no": delivery.vehicle_no,
            "status": delivery.status,
            "pickup_at": delivery.pickup_at,
            "delivered_at": delivery.delivered_at,
            "created_at": delivery.created_at,
        }
        for delivery, listing_name in q.order_by(Delivery.created_at.desc()).all()
    ]

@router.post("/{delivery_id}/claim")
def claim_delivery(delivery_id: int, user=Depends(current_user), db: Session=Depends(get_db)):
    if user.role not in {"volunteer", "admin"}:
        raise HTTPException(403, "Only volunteers can claim deliveries")
    delivery = db.get(Delivery, delivery_id)
    if not delivery:
        raise HTTPException(404, "Delivery not found")
    if delivery.volunteer_id is not None and delivery.volunteer_id != user.id:
        raise HTTPException(409, "This delivery has already been claimed")
    if delivery.status != "assigned":
        raise HTTPException(409, "Only assigned deliveries can be claimed")
    delivery.volunteer_id = user.id
    db.commit()
    return {"id": delivery.id, "volunteer_id": delivery.volunteer_id}

@router.patch("/{delivery_id}/status")
def update_delivery(delivery_id: int, status: str, user=Depends(current_user), db: Session=Depends(get_db)):
    d = db.get(Delivery, delivery_id)
    if not d: raise HTTPException(404, "Delivery not found")
    if user.role != "admin" and (user.role != "volunteer" or d.volunteer_id != user.id):
        raise HTTPException(403, "Not allowed")
    transitions = {
        "assigned": {"picked_up", "cancelled"},
        "picked_up": {"on_the_way", "cancelled"},
        "on_the_way": {"delivered", "cancelled"},
        "delivered": set(),
        "cancelled": set(),
    }
    if status not in transitions.get(d.status, set()):
        raise HTTPException(400, "Invalid status")
    d.status = status
    if status == "picked_up": d.pickup_at = datetime.utcnow()
    if status == "delivered":
        d.delivered_at = datetime.utcnow()
        if d.request_id:
            request = db.get(FoodRequest, d.request_id)
            listing = db.get(FoodListing, d.listing_id)
            if request:
                request.status = "completed"
                if listing:
                    listing.quantity -= request.requested_quantity
                    listing.status = "available" if listing.quantity > 0 else "delivered"
                db.add(Notification(user_id=request.requester_id, title="Food delivered", message=f"Your request for {listing.name if listing else 'food'} has been delivered.", channel="in_app"))
            if listing:
                db.add(Notification(user_id=listing.donor_id, title="Food delivered", message=f"Your listing {listing.name} has been delivered.", channel="in_app"))
    if status == "cancelled" and d.request_id:
        request = db.get(FoodRequest, d.request_id)
        listing = db.get(FoodListing, d.listing_id)
        if request:
            request.status = "cancelled"
        if listing:
            listing.status = "available"
    db.commit()
    return {"status": status}

@router.post("/{delivery_id}/location")
def add_location(delivery_id: int, data: LocationIn, user=Depends(current_user), db: Session=Depends(get_db)):
    d = db.get(Delivery, delivery_id)
    if not d: raise HTTPException(404, "Delivery not found")
    if user.role != "admin" and (user.role != "volunteer" or d.volunteer_id != user.id):
        raise HTTPException(403, "Not allowed")
    point = DeliveryLocation(delivery_id=delivery_id, latitude=data.latitude, longitude=data.longitude)
    db.add(point); db.commit(); db.refresh(point)
    return point

@router.get("/{delivery_id}/locations")
def delivery_locations(delivery_id: int, user=Depends(current_user), db: Session=Depends(get_db)):
    delivery = db.get(Delivery, delivery_id)
    if not delivery:
        raise HTTPException(404, "Delivery not found")
    if user.role != "admin" and user.id not in {delivery.volunteer_id}:
        listing = db.get(FoodListing, delivery.listing_id)
        request = db.get(FoodRequest, delivery.request_id) if delivery.request_id else None
        if user.id != listing.donor_id and (not request or user.id != request.requester_id):
            raise HTTPException(403, "Not allowed")
    return db.query(DeliveryLocation).filter(DeliveryLocation.delivery_id == delivery_id).order_by(DeliveryLocation.recorded_at).all()
