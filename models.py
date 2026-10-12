from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Station(db.Model):
    __tablename__ = "stations"

    id          = db.Column(db.Integer, primary_key=True)
    station_uid = db.Column(db.String(64), unique=True, nullable=False)
    name        = db.Column(db.String(128), nullable=False)
    location    = db.Column(db.String(255))
    api_key     = db.Column(db.String(64), unique=True, nullable=False)
    is_active   = db.Column(db.Boolean, nullable=False, default=True)
    created_at  = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    measurements = db.relationship("Measurement", back_populates="station", cascade="all, delete-orphan")


class Measurement(db.Model):
    __tablename__ = "measurements"

    id          = db.Column(db.BigInteger, primary_key=True)
    station_id  = db.Column(db.Integer, db.ForeignKey("stations.id", ondelete="CASCADE"), nullable=False)
    t           = db.Column(db.Numeric(5, 2), nullable=False)
    h           = db.Column(db.Numeric(5, 2), nullable=False)
    p           = db.Column(db.Numeric(7, 2), nullable=False)
    r           = db.Column(db.Numeric(5, 2), nullable=False)
    ra          = db.Column(db.Integer, nullable=False)
    mq          = db.Column(db.Integer, nullable=False)
    aht         = db.Column(db.Boolean, nullable=False)
    bmp         = db.Column(db.Boolean, nullable=False)
    recorded_at = db.Column(db.DateTime, nullable=False)
    created_at  = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    station = db.relationship("Station", back_populates="measurements")

    __table_args__ = (
        db.Index("idx_station_time", "station_id", "recorded_at"),
        db.Index("idx_recorded_at", "recorded_at"),
    )