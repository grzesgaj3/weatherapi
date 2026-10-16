# Uruchomienie Weather API na małym VPS

Instrukcja dla VPS z 256–512 MB RAM (Debian 12 / Ubuntu 22.04+).

## 1. Wymagania

- VPS 256–512 MB RAM, 1 vCPU (zalecany swap 512 MB).
- Python 3.11+, `python3-venv`.
- Baza: MySQL/MariaDB **albo** SQLite (wariant najmniej pamięciożerny, patrz §9).

## 2. Pakiety systemowe

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
# Jeśli używasz MySQL:
sudo apt install -y mysql-server        # lub: mariadb-server
```

## 3. Katalog i użytkownik

```bash
sudo useradd --system --home /opt/weatherapi --shell /usr/sbin/nologin weatherapi
sudo mkdir -p /opt/weatherapi
sudo chown -R weatherapi:weatherapi /opt/weatherapi
```

Skopiuj projekt do `/opt/weatherapi` (git clone lub rsync).

## 4. Środowisko Pythona

```bash
cd /opt/weatherapi
sudo -u weatherapi python3 -m venv .venv
sudo -u weatherapi .venv/bin/pip install --upgrade pip
sudo -u weatherapi .venv/bin/pip install -r requirements.txt
```

## 5. Baza danych (MySQL — zalecany tuning)

```bash
sudo cp deploy/my-small.cnf /etc/mysql/conf.d/zz-small.cnf
sudo systemctl restart mysql        # lub mariadb
sudo mysql -e "CREATE DATABASE weather_stations CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -e "CREATE USER 'weatherapi'@'localhost' IDENTIFIED BY 'SILNE_HASLO';"
sudo mysql -e "GRANT ALL PRIVILEGES ON weather_stations.* TO 'weatherapi'@'localhost'; FLUSH PRIVILEGES;"
```

## 6. Konfiguracja `.env`

```bash
sudo -u weatherapi cp .env.example .env
sudo -u weatherapi nano .env
```

Ustaw co najmniej:

```dotenv
DB_USER=weatherapi
DB_PASS=SILNE_HASLO
DB_NAME=weather_stations
# Silny sekret admina (min. 16 znaków) – API nie wystartuje ze słabym:
ADMIN_TOKEN=<wynik poniższej komendy>
```

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Migracje bazy:

```bash
sudo -u weatherapi .venv/bin/alembic upgrade head
```

## 7. Usługa systemd

```bash
sudo cp deploy/weatherapi.service /etc/systemd/system/weatherapi.service
sudo systemctl daemon-reload
sudo systemctl enable --now weatherapi
sudo systemctl status weatherapi
```

Usługa nasłuchuje na `127.0.0.1:8000`, uruchamia **1 worker**, z limitami
`MemoryMax=256M` i `CPUQuota=80%`.

Ręczne uruchomienie (bez systemd): `bash deploy/run.sh`.

## 8. Dostęp z zewnątrz

**Wariant A — bez proxy (najlżejszy, bez TLS):** zmień `--host 127.0.0.1`
na `0.0.0.0` w `deploy/weatherapi.service` i ogranicz dostęp firewallem:

```bash
sudo ufw allow 8000/tcp
```

**Wariant B — nginx + TLS (zalecany publicznie):**

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

```nginx
server {
    listen 80;
    server_name api.example.com;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
sudo certbot --nginx -d api.example.com
```

Binding pozostaje na `127.0.0.1` (nginx jako jedyny punkt wejścia).

## 9. Wariant najlżejszy: SQLite (bez MySQL)

Aby całkowicie pominąć serwer MySQL (oszczędność ~100–300 MB RAM), ustaw w `.env`:

```dotenv
DATABASE_URL=sqlite+aiosqlite:////opt/weatherapi/weather.db
DATABASE_URL_SYNC=sqlite:////opt/weatherapi/weather.db
```

i doinstaluj sterownik:

```bash
sudo -u weatherapi .venv/bin/pip install aiosqlite
sudo -u weatherapi .venv/bin/python cli.py init-db   # zamiast alembic dla SQLite
```

> Uwaga: przy SQLite używaj pojedynczego workera (domyślnie tak jest).

## 10. Weryfikacja

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok","version":"1.0.0"}

# Rejestracja stacji (zapisz api_key!)
ADMIN_TOKEN=$(grep ADMIN_TOKEN /opt/weatherapi/.env | cut -d= -f2)
curl -X POST http://127.0.0.1:8000/api/v1/stations \
  -H "X-Admin-Key: $ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"station_uid":"STACJA-001","name":"Ogród"}'

# Pomiar z deszczomierza
curl -X POST http://127.0.0.1:8000/api/v1/measurements \
  -H "X-API-Key: <KLUCZ_API>" -H "Content-Type: application/json" \
  -d '{"value": 12.5}'
```

## 11. Oszczędność pamięci

- `MALLOC_ARENA_MAX=2` — mniejsze rozrastanie się sterty glibc (w unit).
- `PYTHONDONTWRITEBYTECODE=1` — brak plików `.pyc`.
- `MemoryMax`/`CPUQuota` w unicie chronią VPS przed OOM.
- Swap 512 MB: `sudo fallocate -l 512M /swap && sudo mkswap /swap && sudo swapon /swap`.
- `vm.swappiness=10` w `/etc/sysctl.conf`.
- Pole `ENABLE_DOCS=false` (domyślnie) wyłącza `/docs`, `/redoc`, `/openapi.json`.
- Jeśli korzystasz z SQLite, usuń/nie instaluj MySQL (największa oszczędność).

## 12. Logi, aktualizacje

```bash
journalctl -u weatherapi -f            # podgląd na żywo
sudo systemctl restart weatherapi

# Aktualizacja:
cd /opt/weatherapi
sudo -u weatherapi git pull
sudo -u weatherapi .venv/bin/pip install -r requirements.txt
sudo -u weatherapi .venv/bin/alembic upgrade head
sudo systemctl restart weatherapi
```
