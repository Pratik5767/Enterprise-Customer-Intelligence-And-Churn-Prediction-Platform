from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Index, Integer, String, JSON, UniqueConstraint
)
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


class RetentionCampaign(Base):
    __tablename__ = "retention_campaigns"
    __table_args__ = (
        CheckConstraint("holdout_share >= 0 AND holdout_share < 1", name="ck_campaign_holdout_range"),
        CheckConstraint("cost_per_contact >= 0 AND incentive_cost >= 0 AND fixed_cost >= 0", name="ck_campaign_costs_nonneg"),
    )

    campaign_id:        Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_name:      Mapped[str] = mapped_column(String(120), unique=True)
    campaign_type:      Mapped[str] = mapped_column(String(30))
    target_segment:     Mapped[str] = mapped_column(String(200))          # readable description
    selection_rule:     Mapped[dict] = mapped_column(JSON)                # the exact filter used (reproducible)
    owner:              Mapped[str] = mapped_column(String(80), index=True)
    status:             Mapped[str] = mapped_column(String(15), index=True, default="draft")
    start_date:         Mapped[date] = mapped_column(Date)
    end_date:           Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    outcome_window_days: Mapped[int] = mapped_column(Integer, default=90)
    holdout_share:      Mapped[float] = mapped_column(Float, default=0.0)
    randomization_seed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost_per_contact:   Mapped[float] = mapped_column(Float, default=0.0)   # per outreach attempt
    incentive_cost:     Mapped[float] = mapped_column(Float, default=0.0)     # per accepted offer
    fixed_cost:         Mapped[float] = mapped_column(Float, default=0.0)
    value_horizon_months: Mapped[int] = mapped_column(Integer, default=12)
    is_synthetic:       Mapped[bool] = mapped_column(Boolean, default=False)   # True for demo/simulated data
    created_at:         Mapped[datetime] = mapped_column(
                            DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
                        )


class CampaignActivity(Base):
    """
    One row per customer per campaign: the follow-up task for treatment customers, the tracking row for control.
    """
    
    __tablename__ = "campaign_activities"
    __table_args__ = (
        UniqueConstraint("campaign_id", "customer_id", name="uq_activity_campaign_customer"),
        CheckConstraint("contact_attempts >= 0", name="ck_activity_attempts_nonneg"),
        Index("ix_activity_rep_status", "assigned_to", "status"),
    )

    activity_id:                    Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id:                    Mapped[int] = mapped_column(
                                        Integer, ForeignKey("retention_campaigns.campaign_id"), index=True
                                    )
    customer_id:                    Mapped[str] = mapped_column(String(20), ForeignKey("customers.customer_id"), index=True)
    assignment:                     Mapped[str] = mapped_column(String(10))     # "treatment" or "control"
    assigned_to:                    Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    status:                         Mapped[str] = mapped_column(String(15), default="pending")
    follow_up_date:                 Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    contact_attempts:               Mapped[int] = mapped_column(Integer, default=0)
    last_contact_at:                Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome:                        Mapped[Optional[str]] = mapped_column(String(25), nullable=True)  # result of the conversation
    retention_outcome:              Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # retained / churned
    retention_outcome_date:         Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes:                          Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # Snapshot taken at enrolment, so the analysis doesn't depend on tables that change later
    prediction_id:                  Mapped[Optional[int]] = mapped_column(
                                        Integer, ForeignKey("churn_predictions.prediction_id"), nullable=True
                                    )
    probability_at_enrollment:      Mapped[float] = mapped_column(Float)
    risk_level_at_enrollment:       Mapped[str] = mapped_column(String(30))
    priority_segment_at_enrollment: Mapped[str] = mapped_column(String(60))
    priority_rank_at_enrollment:    Mapped[int] = mapped_column(Integer)
    monthly_charges_at_enrollment:  Mapped[float] = mapped_column(Float)
    tenure_at_enrollment:           Mapped[int] = mapped_column(Integer)
    contract_type_at_enrollment:    Mapped[str] = mapped_column(String(30))
    created_at:                     Mapped[datetime] = mapped_column(
                                        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
                                    )
    updated_at:                     Mapped[datetime] = mapped_column(
                                        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                                        onupdate=lambda: datetime.now(timezone.utc)
                                    )

