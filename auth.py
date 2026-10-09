from functools import wraps
from flask import request, g, jsonify
from models import Station

def require_station_api_key(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return jsonify(error="Brak nagłówka X-API-Key"), 401

        station = Station.query.filter_by(api_key=api_key, is_active=True).first()
        if station is None:
            return jsonify(error="Nieprawidłowy lub nieaktywny klucz API"), 401

        g.station = station
        return fn(*args, **kwargs)
    return wrapper