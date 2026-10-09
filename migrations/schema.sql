CREATE DATABASE IF NOT EXISTS weather_stations
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE weather_stations;

CREATE TABLE stations (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    station_uid   VARCHAR(64)  NOT NULL UNIQUE,
    name          VARCHAR(128) NOT NULL,
    location      VARCHAR(255) DEFAULT NULL,
    api_key       VARCHAR(64)  NOT NULL UNIQUE,
    is_active     TINYINT(1)   NOT NULL DEFAULT 1,
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_station_uid (station_uid)
) ENGINE=InnoDB;

CREATE TABLE measurements (
    id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    station_id    INT UNSIGNED NOT NULL,
    temperature   DECIMAL(5,2)  NOT NULL,
    humidity      DECIMAL(5,2)  NOT NULL,
    pressure      DECIMAL(7,2)  NOT NULL,
    co            DECIMAL(7,2)  NOT NULL,
    recorded_at   DATETIME      NOT NULL,
    created_at    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_measurements_station
        FOREIGN KEY (station_id) REFERENCES stations(id)
        ON DELETE CASCADE,
    INDEX idx_station_time (station_id, recorded_at),
    INDEX idx_recorded_at  (recorded_at)
) ENGINE=InnoDB;