from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, g
from marshmallow import ValidationError
from models import db, Measurement
from schemas import MeasurementSchema, MeasurementBatchSchema
from auth import require_station_api_key

bp = Blueprint("measurements", __name__, url_prefix="/api/v1/measurements")

single_schema = MeasurementSchema()
batch_schema  = MeasurementBatchSchema()


def _normalize_recorded_at(data: dict) -> dict:
    """Jeśli brak recorded_at – użyj bieżącego czasu UTC."""
    if not data.get("recorded_at"):
        data["recorded_at"] = datetime.now(timezone.utc)
    else:
        dt = data["recorded_at"]
        # ujednolicamy do naive UTC (MySQL DATETIME bez strefy)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        data["recorded_at"] = dt
    return data


@bp.post("/")
@require_station_api_key
def create_measurements():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify(error="Brak lub nieprawidłowy JSON"), 400

    station = g.station

    # Tryb wsadowy?
    if isinstance(payload, dict) and "measurements" in payload:
        try:
            data = batch_schema.load(payload)
        except ValidationError as err:
            return jsonify(error="Błąd walidacji", details=err.messages), 422
        items = data["measurements"]
        mode = "batch"
    else:
        try:
            data = single_schema.load(payload)
        except ValidationError as err:
            return jsonify(error="Błąd walidacji", details=err.messages), 422
        items = [data]
        mode = "single"

    rows = []
    for item in items:
        item = _normalize_recorded_at(item)
        rows.append(Measurement(
            station_id  = station.id,
            temperature = item["temperature"],
            humidity    = item["humidity"],
            pressure    = item["pressure"],
            co          = item["co"],
            recorded_at = item["recorded_at"],
        ))

    try:
        db.session.bulk_save_objects(rows)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify(error="Błąd zapisu do bazy", details=str(e)), 500

    return jsonify(
        status="ok",
        station=station.station_uid,
        mode=mode,
        inserted=len(rows),
    ), 201


@bp.get("/")
@require_station_api_key
def list_measurements():
    station = g.station
    try:
        limit = min(int(request.args.get("limit", 100)), 1000)
    except ValueError:
        return jsonify(error="Parametr limit musi być liczbą"), 400

    q = Measurement.query.filter_by(station_id=station.id)

    if (frm := request.args.get("from")):
        q = q.filter(Measurement.recorded_at >= _parse_dt(frm))
    if (to := request.args.get("to")):
        q = q.filter(Measurement.recorded_at <= _parse_dt(to))

    rows = q.order_by(Measurement.recorded_at.desc()).limit(limit).all()

    return jsonify(
        station=station.station_uid,
        count=len(rows),
        data=[
            {
                "id": r.id,
                "temperature": float(r.temperature),
                "humidity": float(r.humidity),
                "pressure": float(r.pressure),
                "co": float(r.co),
                "recorded_at": r.recorded_at.replace(tzinfo=timezone.utc).isoformat(),
            }
            for r in rows
        ],
    )


def _parse_dt(value: str) -> datetime:
    """Parsuje ISO 8601 z opcjonalnym 'Z' lub offsetem, zwraca naive UTC."""
    v = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(v)
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt