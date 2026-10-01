from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

# ---------- Auth ----------


class RegisterReq(BaseModel):
    restaurantName: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginReq(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordReq(BaseModel):
    email: EmailStr


class ResetPasswordReq(BaseModel):
    token: str = Field(min_length=10)
    password: str = Field(min_length=6, max_length=128)


class InviteStaffReq(BaseModel):
    email: EmailStr


class AcceptInviteReq(BaseModel):
    token: str = Field(min_length=10)
    name: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=6, max_length=128)


class StaffActiveReq(BaseModel):
    isActive: bool


# ---------- Menu ----------


class CategoryReq(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: Optional[str] = ""
    sortOrder: int = 0
    isActive: bool = True


class OptionReq(BaseModel):
    id: Optional[str] = None
    name: str = Field(min_length=1, max_length=80)
    price: float = 0.0

    @field_validator("price")
    @classmethod
    def non_negative(cls, v):
        if v < 0:
            raise ValueError("Prijs mag niet negatief zijn")
        return round(float(v), 2)


class OptionGroupReq(BaseModel):
    id: Optional[str] = None
    name: str = Field(min_length=1, max_length=80)
    required: bool = False
    multiple: bool = False
    options: List[OptionReq] = []


class MenuItemReq(BaseModel):
    categoryId: str
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = ""
    price: float
    image: Optional[str] = ""
    sortOrder: int = 0
    isAvailable: bool = True
    optionGroups: List[OptionGroupReq] = []

    @field_validator("price")
    @classmethod
    def positive(cls, v):
        if v < 0:
            raise ValueError("Prijs mag niet negatief zijn")
        return round(float(v), 2)


class AvailabilityReq(BaseModel):
    isAvailable: bool


# ---------- Restaurant settings ----------


class ProfileReq(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: Optional[str] = ""
    logo: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    street: Optional[str] = ""
    houseNumber: Optional[str] = ""
    postalCode: Optional[str] = ""
    city: Optional[str] = ""
    country: Optional[str] = "BE"
    defaultLanguage: str = "nl"


class DeliveryZoneReq(BaseModel):
    id: Optional[str] = None
    minDistance: float = 0
    maxDistance: float
    deliveryFee: float
    minimumOrderAmount: float = 0
    enabled: bool = True

    @field_validator("maxDistance", "deliveryFee", "minimumOrderAmount", "minDistance")
    @classmethod
    def non_negative(cls, v):
        if v < 0:
            raise ValueError("Waarde mag niet negatief zijn")
        return round(float(v), 2)


class DeliveryReq(BaseModel):
    deliveryEnabled: bool
    zones: List[DeliveryZoneReq] = []
    freeDeliveryEnabled: bool = False
    freeDeliveryThreshold: float = 0


class DayHoursReq(BaseModel):
    closed: bool = True
    open: str = "11:30"
    close: str = "21:30"


class OpeningHoursReq(BaseModel):
    monday: DayHoursReq
    tuesday: DayHoursReq
    wednesday: DayHoursReq
    thursday: DayHoursReq
    friday: DayHoursReq
    saturday: DayHoursReq
    sunday: DayHoursReq


class SettingsReq(BaseModel):
    orderingEnabled: bool
    pickupEnabled: bool
    orderEmailsEnabled: bool = True
    customerEmailsEnabled: bool = True


# ---------- Public order ----------


class SelectedOptionReq(BaseModel):
    groupId: str
    optionId: str


class OrderItemReq(BaseModel):
    productId: str
    quantity: int = Field(ge=1, le=99)
    selectedOptions: List[SelectedOptionReq] = []


class CustomerReq(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=4, max_length=40)
    email: EmailStr


class DeliveryAddressReq(BaseModel):
    street: str = Field(min_length=1)
    houseNumber: str = Field(min_length=1)
    postalCode: str = Field(min_length=1)
    city: str = Field(min_length=1)
    extra: Optional[str] = ""


class PublicOrderReq(BaseModel):
    orderType: str
    items: List[OrderItemReq] = Field(min_length=1)
    customer: CustomerReq
    deliveryAddress: Optional[DeliveryAddressReq] = None
    notes: Optional[str] = ""
    idempotencyKey: Optional[str] = None

    @field_validator("orderType")
    @classmethod
    def valid_type(cls, v):
        if v not in ("pickup", "delivery"):
            raise ValueError("Ongeldig besteltype")
        return v


class QuoteReq(BaseModel):
    orderType: str
    items: List[OrderItemReq] = Field(min_length=1)
    deliveryAddress: Optional[DeliveryAddressReq] = None

    @field_validator("orderType")
    @classmethod
    def valid_type(cls, v):
        if v not in ("pickup", "delivery"):
            raise ValueError("Ongeldig besteltype")
        return v


class StatusReq(BaseModel):
    status: str
    estimatedMinutes: Optional[int] = None

    @field_validator("estimatedMinutes")
    @classmethod
    def valid_minutes(cls, v):
        if v is None:
            return v
        if not (1 <= int(v) <= 600):
            raise ValueError("Ongeldige tijd")
        return int(v)


class EtaReq(BaseModel):
    estimatedMinutes: int

    @field_validator("estimatedMinutes")
    @classmethod
    def valid_minutes(cls, v):
        if not (1 <= int(v) <= 600):
            raise ValueError("Ongeldige tijd")
        return int(v)


class AdminRestaurantReq(BaseModel):
    restaurantName: str = Field(min_length=2, max_length=80)
    ownerName: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
