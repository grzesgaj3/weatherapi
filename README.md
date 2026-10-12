# Weather API

REST API do zapisywania i odczytywania pomiarów ze stacji pogodowych.

## 1. Wymagania

- Python 3.10 lub nowszy
- MySQL 8 lub MariaDB
- dostęp do portu bazy danych, domyślnie `3306`

## 2. Instalacja

W katalogu projektu utwórz i aktywuj środowisko wirtualne, a następnie zainstaluj zależności:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Skopiuj plik `.env.example` do `.env` i uzupełnij dane dostępowe:

```powershell
Copy-Item .env.example .env
```

Przykładowa konfiguracja:

```dotenv
FLASK_ENV=development
SECRET_KEY=zmien-ten-klucz
DB_HOST=localhost
DB_PORT=3306
DB_USER=weatherapi
DB_PASS=haslo
DB_NAME=weather_stations
```

Przed pierwszym uruchomieniem utwórz bazę i tabele. Dla nowej instalacji użyj aktualnego pliku [migrations/schema.sql](migrations/schema.sql):

```powershell
mysql -u root -p < migrations/schema.sql
```

Alternatywnie można utworzyć tabele przez CLI aplikacji:

```powershell
python cli.py init-db
```

## 3. Rejestracja stacji

Każda stacja musi mieć własny identyfikator i klucz API:

```powershell
python cli.py add-station --uid STACJA-001 --name "Stacja ogród" --location "Warszawa"
```

Polecenie wyświetli klucz API. Należy zachować go po stronie stacji i przekazywać w nagłówku:

```http
X-API-Key: <KLUCZ_API>
```

Lista stacji:

```powershell
python cli.py list-stations
```

## 4. Uruchomienie serwera

Tryb developerski:

```powershell
python app.py
```

Serwer będzie dostępny pod adresem `http://localhost:5000`.

Sprawdzenie stanu:

```powershell
curl http://localhost:5000/health
```

Oczekiwana odpowiedź:

```json
{"status":"ok"}
```

## 5. Format pomiaru

API przyjmuje następujące pola:

| Pole | Typ | Wymagane | Zakres / znaczenie |
| --- | --- | --- | --- |
| `t` | liczba | tak | temperatura w °C, od `-100` do `100` |
| `h` | liczba | tak | wilgotność względna w %, od `0` do `100` |
| `p` | liczba | tak | ciśnienie w hPa, od `0` do `2000` |
| `r` | liczba | tak | względna wilgotność czujnika deszczu w %, od `0` do `100` |
| `ra` | liczba całkowita | tak | surowy odczyt czujnika deszczu, co najmniej `0` |
| `mq` | liczba całkowita | tak | surowy odczyt MQ135, co najmniej `0` |
| `aht` | boolean | tak | czy czujnik AHT jest dostępny |
| `bmp` | boolean | tak | czy czujnik BMP jest dostępny |
| `recorded_at` | ISO 8601 | nie | czas pomiaru; brak oznacza bieżący czas UTC |

Przykładowy obiekt:

```json
{
  "t": 21.5,
  "h": 48.2,
  "p": 1013.25,
  "r": 12.0,
  "ra": 321,
  "mq": 654,
  "aht": true,
  "bmp": false,
  "recorded_at": "2026-10-12T08:45:00Z"
}
```

## 6. Zapisywanie jednego pomiaru

Endpoint:

```http
POST /api/v1/measurements/
```

Przykład:

```powershell
curl -X POST http://localhost:5000/api/v1/measurements/ `
  -H "Content-Type: application/json" `
  -H "X-API-Key: <KLUCZ_API>" `
  -d '{\"t\":21.5,\"h\":48.2,\"p\":1013.25,\"r\":12.0,\"ra\":321,\"mq\":654,\"aht\":true,\"bmp\":false}'
```

Poprawna odpowiedź ma status `201`:

```json
{
  "status": "ok",
  "station": "STACJA-001",
  "mode": "single",
  "inserted": 1
}
```

## 7. Zapisywanie pomiarów wsadowo

W jednym żądaniu można przesłać od 1 do 1000 pomiarów:

```powershell
curl -X POST http://localhost:5000/api/v1/measurements/ `
  -H "Content-Type: application/json" `
  -H "X-API-Key: <KLUCZ_API>" `
  -d '{\"measurements\":[{\"t\":21.5,\"h\":48.2,\"p\":1013.25,\"r\":12,\"ra\":321,\"mq\":654,\"aht\":true,\"bmp\":false},{\"t\":21.7,\"h\":48.0,\"p\":1013.1,\"r\":11,\"ra\":318,\"mq\":650,\"aht\":true,\"bmp\":false}]}'
```

## 8. Odczyt pomiarów

Endpoint:

```http
GET /api/v1/measurements/
```

Parametry opcjonalne:

- `limit` — liczba wyników, domyślnie `100`, maksymalnie `1000`
- `from` — początek zakresu czasu w ISO 8601
- `to` — koniec zakresu czasu w ISO 8601

Przykład:

```powershell
curl "http://localhost:5000/api/v1/measurements/?limit=50&from=2026-10-12T00:00:00Z&to=2026-10-12T23:59:59Z" `
  -H "X-API-Key: <KLUCZ_API>"
```

Przykładowa odpowiedź:

```json
{
  "station": "STACJA-001",
  "count": 1,
  "data": [
    {
      "id": 1,
      "t": 21.5,
      "h": 48.2,
      "p": 1013.25,
      "r": 12.0,
      "ra": 321,
      "mq": 654,
      "aht": true,
      "bmp": false,
      "recorded_at": "2026-10-12T08:45:00+00:00"
    }
  ]
}
```

Wyniki są sortowane od najnowszego do najstarszego.

## 9. Błędy HTTP

| Status | Znaczenie |
| --- | --- |
| `400` | brak lub niepoprawny JSON albo niepoprawny parametr `limit` |
| `401` | brak, niepoprawny lub nieaktywny klucz API |
| `404` | nie znaleziono endpointu |
| `405` | niedozwolona metoda HTTP |
| `422` | dane nie przeszły walidacji |
| `500` | błąd zapisu lub błąd serwera |

Przykładowa odpowiedź walidacyjna:

```json
{
  "error": "Błąd walidacji",
  "details": {
    "h": ["Missing data for required field."]
  }
}
```

## 10. Kolejność uruchomienia od zera

1. Utwórz bazę według [migrations/schema.sql](migrations/schema.sql).
2. Skonfiguruj `.env`.
3. Zainstaluj zależności z [requirements.txt](requirements.txt).
4. Uruchom `python cli.py add-station ...`.
5. Uruchom `python app.py`.
6. Wyślij żądanie `GET /health`.
7. Wyślij testowy pomiar `POST /api/v1/measurements/`.
