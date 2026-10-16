# Weather API

REST API (FastAPI) do odbioru pomiarów opadu z deszczomierza oraz do wystawiania
stacji zleceń, np. **czyszczenia deszczomierza**.

Komunikacja odbywa się w dwóch kierunkach:

- **stacja → serwer**: stacja wysyła pomiar opadu (`POST /api/v1/measurements`),
- **serwer → stacja**: serwer wystawia zlecenie, a stacja je pobiera i kwituje
  (model *pull*, działa za NAT-em).

## 1. Wymagania

- Python 3.11+
- MySQL 8 lub MariaDB
- dostęp do portu bazy, domyślnie `3306`

## 2. Instalacja

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Skopiuj konfigurację i uzupełnij dane:

```bash
cp .env.example .env
```

```dotenv
HOST=0.0.0.0
PORT=8000
DB_HOST=localhost
DB_PORT=3306
DB_USER=weatherapi
DB_PASS=haslo
DB_NAME=weather_stations
ADMIN_TOKEN=zmien-na-dlugi-losowy-sekret
```

`ADMIN_TOKEN` musi mieć min. 16 znaków i nie może być wartością domyślną — w
przeciwnym razie API odmówi startu (fail-fast). Wygeneruj go np.:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 3. Migracje bazy

Preferowany sposób to Alembic:

```bash
alembic upgrade head
```

Szybki start w developmencie (tworzy tabele z modeli):

```bash
python cli.py init-db
```

## 4. Rejestracja stacji

API administratora (klucz raz, potem nie jest już pokazywany):

```bash
curl -X POST http://localhost:8000/api/v1/stations \
  -H "X-Admin-Key: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"station_uid":"STACJA-001","name":"Ogród","location":"Warszawa"}'
```

Odpowiedź zawiera `api_key` — zachowaj go po stronie stacji.

Alternatywnie przez CLI:

```bash
python cli.py add-station --uid STACJA-001 --name "Ogród" --location "Warszawa"
python cli.py list-stations
```

## 5. Uruchomienie serwera

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Dokumentacja interaktywna: <http://localhost:8000/docs>

Health check:

```bash
curl http://localhost:8000/health
```

## 6. Autoryzacja

| Rola | Nagłówek | Uwagi |
| --- | --- | --- |
| Stacja | `X-API-Key: <klucz stacji>` | klucz generowany przy rejestracji, w bazie trzymany jako hash |
| Administrator | `X-Admin-Key: <ADMIN_TOKEN>` lub `Authorization: Bearer <ADMIN_TOKEN>` | z `.env` |

## 7. Push pomiaru (stacja → serwer)

Endpoint:

```http
POST /api/v1/measurements
```

| Pole | Typ | Wymagane | Znaczenie |
| --- | --- | --- | --- |
| `value` | liczba | tak | opad w mm, `>= 0` |
| `recorded_at` | ISO 8601 | nie | czas zakodowany odebrany ze stacji radiowej (normalizowany do UTC) |

```bash
curl -X POST http://localhost:8000/api/v1/measurements \
  -H "X-API-Key: <KLUCZ_API>" \
  -H "Content-Type: application/json" \
  -d '{"value": 12.5, "recorded_at": "2026-10-12T08:45:00Z"}'
```

Odpowiedź `201`:

```json
{
  "value": 12.5,
  "received_at": "2026-10-16T10:15:30Z",
  "recorded_at": "2026-10-12T08:45:00Z"
}
```

- `received_at` — czas przyjęcia na serwerze (UTC), ustawiany automatycznie.
- `recorded_at` — opcjonalny czas zakodowany w odebranej ramce radiowej (UTC).

Odczyt własnych pomiarów przez stację: `GET /api/v1/measurements?limit=100`
(zwraca envelope strony, patrz sekcja „Paginacja").

## 8. Zlecenia (np. czyszczenie deszczomierza)

### Cykl życia

```
pending ──(stacja pobiera)──► delivered ──(ack in_progress)──► in_progress
   │                                                            │
   └──(admin anuluje)──► cancelled          ack completed/failed ┘──► completed / failed
   └──(TTL minie)──────► expired
```

Reguły:

- jednorazowo maksymalnie **1 aktywne** zlecenie danego typu na stację
  (`MAX_ACTIVE_COMMANDS_PER_STATION`, domyślnie `1`) — kolejne zwraca `409`,
- zlecenie nieodebrane wygasa po `COMMAND_TTL_MINUTES` (domyślnie `60`),
- `Device` może tylko pobierać i kwitować zlecenia swojej stacji.

### Wystawienie zlecenia (admin)

```http
POST /api/v1/stations/{station_uid}/commands
```

| Pole | Typ | Wymagane | Znaczenie |
| --- | --- | --- | --- |
| `type` | string | tak | `clean_rain_gauge`, `reset`, `calibrate` |
| `params` | objekt | nie | parametry przekazywane stacji |

```bash
curl -X POST http://localhost:8000/api/v1/stations/STACJA-001/commands \
  -H "X-Admin-Key: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type": "clean_rain_gauge", "params": {"cycles": 3}}'
```

Odpowiedź `201`:

```json
{
  "uid": "3f3c1b2e-...-a1",
  "station_id": 1,
  "type": "clean_rain_gauge",
  "status": "pending",
  "params": {"cycles": 3},
  "result": null,
  "created_by": "admin",
  "created_at": "2026-10-16T10:20:00Z",
  "delivered_at": null,
  "started_at": null,
  "completed_at": null,
  "expires_at": "2026-10-16T11:20:00Z"
}
```

Pozostałe endpointy admina:

- `GET /api/v1/stations/{uid}/commands?status=pending`
- `GET /api/v1/commands/{uid}`
- `DELETE /api/v1/commands/{uid}` — anulowanie (`pending`/`delivered`)
- `GET /api/v1/stations`, `GET /api/v1/stations/{uid}`, `PATCH /api/v1/stations/{uid}`

### Pobranie zleceń (stacja)

Podgląd (tylko odczyt, nie zmienia stanu):

```bash
curl "http://localhost:8000/api/v1/commands?status=pending" \
  -H "X-API-Key: <KLUCZ_API>"
```

Pobranie (claim) — oznacza pobrane `pending` jako `delivered`:

```bash
curl -X POST http://localhost:8000/api/v1/commands/claim \
  -H "X-API-Key: <KLUCZ_API>"
```

### Kwitowanie (stacja)
```http
POST /api/v1/commands/{uid}/ack
```

```bash
curl -X POST http://localhost:8000/api/v1/commands/<UID>/ack \
  -H "X-API-Key: <KLUCZ_API>" \
  -H "Content-Type: application/json" \
  -d '{"status": "completed", "result": {"duration_ms": 1200}}'
```

`status`: `in_progress` | `completed` | `failed`. Zamkniętego zlecenia nie można
kwitować ponownie (`409`).

## 9. Błędy HTTP

Ujednolicony envelope:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Błąd walidacji danych",
    "details": [{"field": "value", "message": "Input should be greater than or equal to 0"}]
  }
}
```

| Status | Znaczenie |
| --- | --- |
| `400` | niepoprawne żądanie |
| `401` | brak/nieprawidłowy klucz lub token |
| `404` | nie znaleziono zasobu |
| `409` | konflikt (zlecenie/stacja już istnieje, zlecenie zamknięte) |
| `413` | ciało żądania przekracza `MAX_BODY_BYTES` |
| `422` | dane nie przeszły walidacji |
| `429` | przekroczony limit żądań (`Retry-After`) |
| `500` | błąd serwera |

## 10. Paginacja

Listy (`/measurements`, `/commands`, `/stations/{uid}/commands`,
`/stations/{uid}/measurements`) zwracają envelope strony:

```json
{
  "data": [ /* elementy */ ],
  "next_cursor": "eyJpZCI6MTIzfQ",
  "has_more": true
}
```

Kolejną stronę pobierz, przekazując `next_cursor` jako parametr `cursor`
(oraz ten sam `limit`). Brak `next_cursor` oznacza koniec danych.

## 11. Rate limiting

Każde żądanie do `/api/v1/*` podlega limitowi `RATE_LIMIT_PER_MIN` na minutę,
kluczowanemu po hashu `X-API-Key`/`X-Admin-Key` lub adresie IP. Odpowiedzi
zawierają nagłówki `X-RateLimit-*`; przekroczenie zwraca `429` z `Retry-After`.

## 12. Testy

```bash
pip install -r requirements-dev.txt
pytest -q
```

## 13. Struktura projektu

```
app/
  main.py            # aplikacja FastAPI + middleware
  config.py          # ustawienia (pydantic-settings, walidacja sekretu)
  database.py        # silnik async + sesje
  models/            # Station, Measurement, Command
  schemas/           # modele Pydantic (request/response, Page)
  api/
    deps.py          # auth: stacja / admin
    errors.py        # globalny envelope błędów
    ratelimit.py     # slowapi (limit per stacja/klient)
    middleware.py    # limit rozmiaru body
    pagination.py    # paginacja kursorowa
    v1/              # measurements, commands, stations, health
  services/          # logika zleceń, hashowanie kluczy
alembic/             # migracje
cli.py               # CLI (init-db, add-station, list-stations)
tests/               # pytest
```

## 14. Kolejność uruchomienia od zera

1. Utwórz bazę i użytkownika w MySQL.
2. `cp .env.example .env` i uzupełnij dane (w tym silny `ADMIN_TOKEN`).
3. `pip install -r requirements.txt`.
4. `alembic upgrade head` (albo `python cli.py init-db`).
5. Zarejestruj stację i zapisz `api_key`.
6. `uvicorn app.main:app --reload`.
7. `GET /health`, potem testowy `POST /api/v1/measurements`.
8. `POST /api/v1/stations/{uid}/commands` z typem `clean_rain_gauge`.
9. Stacja: `POST /api/v1/commands/claim`, następnie `POST /api/v1/commands/{uid}/ack`.

## 15. Wdrożenie na małym VPS

Pełna instrukcja: [DEPLOY.md](DEPLOY.md). Skrót:

- serwer: **uvicorn, 1 worker**, `--no-access-log --no-server-header --limit-concurrency 50`;
- pliki: [`deploy/weatherapi.service`](deploy/weatherapi.service),
  [`deploy/run.sh`](deploy/run.sh), [`deploy/my-small.cnf`](deploy/my-small.cnf);
- `ENABLE_DOCS=false` (domyślnie) wyłącza `/docs`, `/redoc`, `/openapi.json`;
- `MALLOC_ARENA_MAX=2`, `PYTHONDONTWRITEBYTECODE=1` i limity systemd (`MemoryMax`);
- dla najlżejszej konfiguracji można pominąć MySQL: `DATABASE_URL=sqlite+aiosqlite:///...`.

Orientacyjny ślad pamięciowy samego API: **~90 MB RSS** (Python + FastAPI +
SQLAlchemy + Pydantic) + ~9 MB narzutu serwera.
