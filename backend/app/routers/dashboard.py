from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.models import Delivery, FoodListing, FoodRequest, ImpactMetric
from ..security import current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
def stats(user=Depends(current_user), db: Session = Depends(get_db)):
    listings = db.query(FoodListing)
    requests = db.query(FoodRequest)
    deliveries = db.query(Delivery)

    if user.role == "donor":
        listings = listings.filter(FoodListing.donor_id == user.id)
        requests = requests.join(FoodListing, FoodRequest.listing_id == FoodListing.id).filter(
            FoodListing.donor_id == user.id
        )
        deliveries = deliveries.join(FoodListing, Delivery.listing_id == FoodListing.id).filter(
            FoodListing.donor_id == user.id
        )
    elif user.role in {"ngo", "community_worker"}:
        requests = requests.filter(FoodRequest.requester_id == user.id)
        deliveries = deliveries.join(FoodRequest, Delivery.request_id == FoodRequest.id).filter(
            FoodRequest.requester_id == user.id
        )
    elif user.role == "volunteer":
        deliveries = deliveries.filter(
            (Delivery.volunteer_id == user.id) | (Delivery.volunteer_id.is_(None))
        )
    elif user.role != "admin":
        listings = listings.filter(FoodListing.status == "available")

    rescued = db.query(func.coalesce(func.sum(ImpactMetric.food_rescued_kg), 0)).scalar()
    return {
        "listings": listings.count(),
        "requests": requests.count(),
        "deliveries": deliveries.count(),
        "available_listings": db.query(FoodListing).filter(FoodListing.status == "available").count(),
        "food_rescued_kg": float(rescued or 0),
    }
