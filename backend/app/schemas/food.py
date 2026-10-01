from pydantic import BaseModel, Field
from datetime import datetime

class FoodCreate(BaseModel):
    name: str
    type: str = "Cooked"
    quantity: float = Field(gt=0)
    unit: str = "kg"
    preparation_time: datetime | None = None
    expiry_hours: float = Field(default=2, gt=0)
    dietary: str | None = None
    notes: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None

class FoodOut(BaseModel):
    id: int
    name: str
    food_type: str
    quantity: float
    unit: str
    status: str
    latitude: float | None
    longitude: float | None
    address: str | None
    preparation_time: datetime | None = None
    expiry_at: datetime | None = None
    dietary_labels: str | None = None
    notes: str | None = None
    model_config = {"from_attributes": True}
