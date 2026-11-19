from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Index, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column
from src.db.session import Base



class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint("tenure >= 0", name="ck_customers_tenure_nonneg"),
        CheckConstraint("monthly_charges > 0", name="ck_customers_monthly_positive"),
    )

    customer_id:            Mapped[str] = mapped_column(String(20), primary_key=True)
    gender:                 Mapped[str] = mapped_column(String(10))
    senior_citizen:         Mapped[str] = mapped_column(String(3))
    partner:                Mapped[str] = mapped_column(String(3))
    dependents:             Mapped[str] = mapped_column(String(3))
    tenure:                 Mapped[int] = mapped_column(Integer)
    phone_service:          Mapped[str] = mapped_column(String(3))
    multiple_lines:         Mapped[str] = mapped_column(String(30))
    internet_service:       Mapped[str] = mapped_column(String(30))
    online_security:        Mapped[str] = mapped_column(String(30))
    online_backup:          Mapped[str] = mapped_column(String(30))
    device_protection:      Mapped[str] = mapped_column(String(30))
    tech_support:           Mapped[str] = mapped_column(String(30))
    streaming_tv:           Mapped[str] = mapped_column(String(30))
    streaming_movies:       Mapped[str] = mapped_column(String(30))
    contract_type:          Mapped[str] = mapped_column(String(30), index=True)
    paperless_billing:      Mapped[str] = mapped_column(String(3))
    payment_method:         Mapped[str] = mapped_column(String(40))
    monthly_charges:        Mapped[float] = mapped_column(Float)
    total_charges:          Mapped[float] = mapped_column(Float)
    subscription_start:     Mapped[date] =  mapped_column(Date)
    subscription_status:    Mapped[str] = mapped_column(String(10), index=True)
    is_outlier:             Mapped[bool] = mapped_column(Boolean, default=False)
    created_at:             Mapped[datetime] = mapped_column(
                                            DateTime(timezone=True), 
                                            default=lambda: datetime.now(timezone.utc)
                                        )


class ModelExperiment(Base):
    __tablename__ = "model_experiments"

    experiment_id:      Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_name:         Mapped[str] = mapped_column(String(80), index=True)
    model_version:      Mapped[str] = mapped_column(String(20))
    dataset_version:    Mapped[str] = mapped_column(String(40))
    metrics:            Mapped[dict] = mapped_column(JSON)
    is_selected:        Mapped[bool] = mapped_column(Boolean, default=False)
    created_at:         Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ChurnPrediction(Base):
    """
    Append-only history: every scoring run adds rows; nothing is overwritten.
    """
    
    __tablename__ = "churn_predictions"
    __table_args__ = (
        CheckConstraint("probability >= 0 AND probability <= 1", name="ck_pred_probability_range"),
        Index("ix_pred_customer_date", "customer_id", "prediction_date"),
    )

    prediction_id:      Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # NULL is allowed so Day 4's API can store what-if predictions for records not in `customers`
    customer_id:        Mapped[Optional[str]] = mapped_column(
                            String(20), 
                            ForeignKey("customers.customer_id"), 
                            nullable=True
                        )
    batch_id:           Mapped[str] = mapped_column(String(40), index=True)       # groups one scoring run
    source:             Mapped[str] = mapped_column(String(10), default="batch")    # "batch" or "api"
    model_version:      Mapped[str] = mapped_column(String(20), index=True)
    probability:        Mapped[float] = mapped_column(Float)
    threshold:          Mapped[float] = mapped_column(Float)
    flagged_for_review: Mapped[bool] = mapped_column(Boolean)
    risk_level:         Mapped[str] = mapped_column(String(30), index=True)
    value_tier:         Mapped[str] = mapped_column(String(30))
    priority_segment:   Mapped[str] = mapped_column(String(60))
    priority_rank:      Mapped[int] = mapped_column(Integer)
    top_risk_factors:   Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    top_protective_factors: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    prediction_date:    Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at:         Mapped[datetime] = mapped_column(
                            DateTime(timezone=True), 
                            default=lambda: datetime.now(timezone.utc)
                        )

