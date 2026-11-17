"""An agency event is linked to the existing production project."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class ProductionEvent(Base):
    __tablename__ = "production_events"
    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    venue = Column(String(500))
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    forecast_budget = Column(Numeric(14, 2))
    archived = Column(Boolean, nullable=False, default=False)


class EventArtist(Base):
    __tablename__ = "production_event_artists"
    __table_args__ = (UniqueConstraint("event_id", "artist_id"),)
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("production_events.id"), nullable=False)
    artist_id = Column(UUID(as_uuid=True), ForeignKey("discovery_artists.id"), nullable=False)


class EventExpense(Base):
    __tablename__ = "production_event_expenses"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("production_events.id"), nullable=False, index=True)
    description = Column(String(500), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
