from datetime import date, datetime, timezone
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from src.db.session import Base



class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint("tenure >= 0", name="ck_customers_tenure_nonneg"),
        CheckConstraint("monthly_charges > 0", name="ck_customers_monthly_positive"),
    )

    customer_id: Mapped[str] =          mapped_column(String(20), primary_key=True)
    gender: Mapped[str] =               mapped_column(String(10))
    senior_citizen: Mapped[str] =       mapped_column(String(3))
    partner: Mapped[str] =              mapped_column(String(3))
    dependents: Mapped[str] =           mapped_column(String(3))
    tenure: Mapped[int] =               mapped_column(Integer)
    phone_service: Mapped[str] =        mapped_column(String(3))
    multiple_lines: Mapped[str] =       mapped_column(String(30))
    internet_service: Mapped[str] =     mapped_column(String(30))
    online_security: Mapped[str] =      mapped_column(String(30))
    online_backup: Mapped[str] =        mapped_column(String(30))
    device_protection: Mapped[str] =    mapped_column(String(30))
    tech_support: Mapped[str] =         mapped_column(String(30))
    streaming_tv: Mapped[str] =         mapped_column(String(30))
    streaming_movies: Mapped[str] =     mapped_column(String(30))
    contract_type: Mapped[str] =        mapped_column(String(30), index=True)
    paperless_billing: Mapped[str] =    mapped_column(String(3))
    payment_method: Mapped[str] =       mapped_column(String(40))
    monthly_charges: Mapped[float] =    mapped_column(Float)
    total_charges: Mapped[float] =      mapped_column(Float)
    subscription_start: Mapped[date] =  mapped_column(Date)
    subscription_status: Mapped[str] =  mapped_column(String(10), index=True)
    is_outlier: Mapped[bool] =          mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] =      mapped_column(
                                            DateTime(timezone=True), 
                                            default=lambda: datetime.now(timezone.utc)
                                        )

    