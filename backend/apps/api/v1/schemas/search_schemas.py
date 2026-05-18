from pydantic import BaseModel, Field
from datetime import date
from typing import List, Optional, Dict, Any

# ========== REQUEST SCHEMAS ==========
class HotelRatesRequest(BaseModel):
    hotel_id: str = Field(..., description="Hotel identifier (e.g., lp1897)")
    check_in: date = Field(..., description="Check-in date YYYY-MM-DD")
    check_out: date = Field(..., description="Check-out date YYYY-MM-DD")
    guests: int = Field(2, ge=1, le=10, description="Number of adults")
    currency: str = Field("USD", description="Currency code")

# ========== ESSENTIAL RESPONSE FIELDS (What agents need) ==========
class RateEssential(BaseModel):
    """Essential rate information for booking"""
    rate_id: str
    room_name: str
    board_type: str
    board_name: str
    supplier_price: float  # Original price from supplier
    commission_percent: float
    commission_amount: float
    final_price: float  # Price after commission
    currency: str
    cancellation_deadline: Optional[str] = None
    refundable: bool = True
    payment_types: List[str] = []

class RoomTypeEssential(BaseModel):
    """Essential room information"""
    room_type_id: str
    offer_id: str
    supplier: str
    rates: List[RateEssential]

class HotelEssential(BaseModel):
    """Essential hotel information"""
    hotel_id: str
    name: str
    address: str
    rating: float
    main_photo: str

class SearchResponseEssential(BaseModel):
    """Simplified response for agents"""
    hotel: HotelEssential
    check_in: str
    check_out: str
    nights: int
    rooms: List[RoomTypeEssential]
    total_suppliers: int