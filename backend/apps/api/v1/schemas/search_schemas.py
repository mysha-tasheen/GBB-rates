from datetime import date
from typing import List, Optional

from django.conf import settings
from pydantic import BaseModel, Field

from apps.api.v1.schemas.currency_codes import WholesalerCurrency

_CURRENCY_FIELD = Field(
    default=WholesalerCurrency.USD,
    description=(
        "Wholesaler pricing currency (e.g. FJD for Fiji). "
        "Selectable in API docs; full list with country names: GET /currencies"
    ),
)


class Country(BaseModel):
    code: str = Field(..., description="ISO-2 country code (e.g. US, GB)")
    name: str = Field(..., description="Country name")


class CountriesResponse(BaseModel):
    countries: List[Country]
    total: int


class Currency(BaseModel):
    code: str = Field(..., description="ISO 4217 code for rates and bookings (e.g. FJD, USD)")
    name: str = Field(..., description="Currency display name")
    countries: List[str] = Field(
        default_factory=list,
        description="Countries where this currency is used (from supplier reference data)",
    )


class CurrenciesResponse(BaseModel):
    currencies: List[Currency]
    total: int


class HotelSummary(BaseModel):
    hotel_id: str = Field(..., description="Use this ID on POST /hotel-rates")
    name: str
    city: str
    country_code: str
    address: str
    rating: float = Field(..., description="Star rating")
    main_photo: str = ""


class HotelListResponse(BaseModel):
    country_code: str
    city_name: Optional[str] = None
    hotels: List[HotelSummary]
    total: int
    offset: int
    limit: int


class HotelMinRatesRequest(BaseModel):
    hotel_ids: List[str] = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Hotel IDs from GET /hotels (max 200)",
    )
    check_in: date = Field(..., description="Check-in date YYYY-MM-DD")
    check_out: date = Field(..., description="Check-out date YYYY-MM-DD")
    guests: int = Field(2, ge=1, le=10, description="Number of adults")
    currency: WholesalerCurrency = _CURRENCY_FIELD
    guest_nationality: str = Field(
        default_factory=lambda: settings.NUITEE_GUEST_NATIONALITY,
        min_length=2,
        max_length=2,
        description="ISO-2 from GET /countries",
    )
    commission: float = Field(
        0,
        ge=0,
        description="Flat amount added to each min price (0 = no extra markup)",
    )


class HotelMinRate(BaseModel):
    hotel_id: str
    price: float = Field(..., description="Minimum price (markup included)")
    offer_id: str = Field(
        ...,
        description="Pass to POST /bookings/prebook (from a fresh rates search)",
    )


class HotelMinRatesResponse(BaseModel):
    check_in: str
    check_out: str
    currency: str
    rates: List[HotelMinRate]
    total: int


class HotelRatesRequest(BaseModel):
    hotel_id: str = Field(..., description="From GET /hotels (e.g. lp1897)")
    check_in: date = Field(..., description="Check-in date YYYY-MM-DD")
    check_out: date = Field(..., description="Check-out date YYYY-MM-DD")
    guests: int = Field(2, ge=1, le=10, description="Number of adults")
    currency: WholesalerCurrency = _CURRENCY_FIELD
    guest_nationality: str = Field(
        default_factory=lambda: settings.NUITEE_GUEST_NATIONALITY,
        min_length=2,
        max_length=2,
        description="ISO-2 from GET /countries (e.g. US, GB)",
    )
    commission: float = Field(
        0,
        ge=0,
        description="Flat amount added to each rate price (0 = no extra markup)",
    )


class RateEssential(BaseModel):
    rate_id: str
    room_name: str
    board_type: str
    board_name: str
    price: float = Field(..., description="Total price for the agent (markup included)")
    currency: str
    cancellation_deadline: Optional[str] = None
    refundable: bool = True
    payment_types: List[str] = []


class RoomTypeEssential(BaseModel):
    room_type_id: str
    offer_id: str = Field(
        ...,
        description="Pass to POST /bookings/prebook (not rate_id)",
    )
    rates: List[RateEssential]


class HotelEssential(BaseModel):
    hotel_id: str
    name: str
    address: str
    rating: float
    main_photo: str


class SearchResponseEssential(BaseModel):
    hotel: HotelEssential
    check_in: str
    check_out: str
    nights: int
    rooms: List[RoomTypeEssential]
    total_offers: int
