import pytest
import sqlite3
import os
import tempfile
from datetime import date, timedelta
import database

@pytest.fixture
def memory_db(monkeypatch):
    temp_fd, temp_path = tempfile.mkstemp()
    os.close(temp_fd)
    monkeypatch.setattr(database, 'DB_PATH', temp_path)
    database.init_db()
    yield
    os.remove(temp_path)

def test_init_db_and_insert(memory_db):
    sample_rows = [
        {"regionName": "北部地區", "dataDate": "2026-04-14", "min": 20.0, "max": 25.0}
    ]
    inserted = database.insert_forecasts(sample_rows)
    assert inserted == 1
    
    regions = database.get_regions()
    assert "北部地區" in regions
    
    forecasts = database.get_forecasts("北部地區")
    assert len(forecasts) == 1
    assert forecasts[0]["min"] == 20.0
    
def test_upsert(memory_db):
    sample_rows = [
        {"regionName": "中部地區", "dataDate": "2026-04-14", "min": 22.0, "max": 28.0}
    ]
    database.insert_forecasts(sample_rows)
    
    # Update with new values
    sample_rows_update = [
        {"regionName": "中部地區", "dataDate": "2026-04-14", "min": 21.0, "max": 29.0}
    ]
    database.insert_forecasts(sample_rows_update)
    
    forecasts = database.get_forecasts("中部地區")
    assert len(forecasts) == 1
    assert forecasts[0]["min"] == 21.0
    assert forecasts[0]["max"] == 29.0

def test_air_stations_crud(memory_db):
    stations = [{
        "station_id": "TEST_001",
        "name": "測試測站",
        "lat": 24.123,
        "lon": 120.456,
        "station_type": "空氣盒子觀測點",
        "pm25": 12.5,
        "temperature": 28.5,
        "humidity": 65.0,
        "status": "active",
        "updated_at": "2026-09-23 12:00:00",
        "history": [
            {"time": "12:00", "pm25": 12.5, "temperature": 28.5, "humidity": 65.0}
        ]
    }]
    inserted = database.insert_air_stations(stations)
    assert inserted == 1
    
    stns = database.get_air_stations()
    assert len(stns) == 1
    assert stns[0]["station_id"] == "TEST_001"
    assert stns[0]["pm25"] == 12.5
    
    hist = database.get_station_history("TEST_001")
    assert len(hist) == 1
    assert hist[0]["pm25"] == 12.5

def test_unchanged_station_data_is_not_written_again(memory_db):
    station = {
        "station_id": "STABLE_001",
        "name": "穩定測站",
        "lat": 24.123,
        "lon": 120.456,
        "station_type": "空氣盒子觀測點",
        "pm25": 12.5,
        "temperature": 28.5,
        "humidity": 65.0,
        "status": "active",
        "updated_at": "2026-09-23 12:00:00",
        "history": [
            {"time": "12:00", "pm25": 12.5, "temperature": 28.5, "humidity": 65.0}
        ],
    }

    assert database.insert_air_stations([station]) == 1
    same_reading_new_fetch_time = {
        **station,
        "updated_at": "2026-09-23 12:05:00",
    }
    assert database.insert_air_stations([same_reading_new_fetch_time]) == 0
    assert database.get_snapshot_count() == 1
    assert len(database.get_update_logs()) == 1
    assert database.get_station_histories(["STABLE_001"])["STABLE_001"][0]["pm25"] == 12.5

def test_changed_station_data_creates_new_snapshot(memory_db):
    station = {
        "station_id": "CHANGED_001",
        "name": "變動測站",
        "lat": 24.123,
        "lon": 120.456,
        "station_type": "空氣盒子觀測點",
        "pm25": 12.5,
        "temperature": 28.5,
        "humidity": 65.0,
        "status": "active",
        "updated_at": "2026-09-23 12:00:00",
    }

    assert database.insert_air_stations([station]) == 1
    changed_station = {**station, "pm25": 18.0, "updated_at": "2026-09-23 12:05:00"}
    assert database.insert_air_stations([changed_station]) == 1
    assert database.get_snapshot_count() == 2
    assert database.get_air_stations()[0]["pm25"] == 18.0

def test_update_station_regions_and_filter(memory_db):
    database.insert_air_stations([{
        "station_id": "YILAN_001",
        "name": "宜蘭測站",
        "lat": 24.75,
        "lon": 121.75,
        "region": "東部地區",
        "station_type": "空氣盒子觀測點",
        "pm25": 12.5,
        "temperature": 28.5,
        "humidity": 65.0,
        "status": "active",
        "updated_at": "2026-09-23 12:00:00",
    }])

    database.update_station_regions([("YILAN_001", "東北部地區")])

    assert len(database.get_air_stations(region="東北部地區")) == 1
    assert database.get_air_stations(region="東部地區") == []

def test_seven_day_forecasts_are_persisted_and_read_by_station(memory_db):
    forecast = {
        "station_id": "FORECAST_001",
        "forecast_date": "2026-09-24",
        "weekday": "(四)",
        "weather": "⛅ 多雲",
        "min_temp": 24.0,
        "max_temp": 30.0,
        "humidity": 72.0,
        "pop": 30,
        "description": "多雲時晴",
        "updated_at": "2026-09-24 08:00:00",
    }

    assert database.has_7day_forecasts() is False
    assert database.insert_7day_forecasts([forecast]) == 1
    assert database.has_7day_forecasts() is True
    assert database.get_7day_forecasts("FORECAST_001")[0]["humidity"] == 72.0
    assert database.get_7day_forecasts("OTHER_STATION") == []

    assert database.insert_7day_forecasts([forecast]) == 0

def test_find_stations_needing_seven_day_forecasts(memory_db):
    stations = [
        {
            "station_id": station_id,
            "name": station_id,
            "lat": 24.0,
            "lon": 121.0,
            "region": "東部地區",
            "station_type": "空氣盒子觀測點",
            "pm25": 10.0,
            "temperature": 25.0,
            "humidity": 60.0,
            "status": "active",
            "updated_at": "2026-09-24 08:00:00",
        }
        for station_id in ("CACHED", "MISSING")
    ]
    database.insert_air_stations(stations)
    database.insert_7day_forecasts([{
        "station_id": "CACHED",
        "forecast_date": (date.today() + timedelta(days=offset)).isoformat(),
        "weekday": "(四)",
        "weather": "⛅ 多雲",
        "min_temp": 24.0,
        "max_temp": 30.0,
        "humidity": 72.0,
        "pop": 30,
        "updated_at": "2026-09-24 08:00:00",
    } for offset in range(7)])

    assert database.get_station_ids_needing_7day_forecasts(["CACHED", "MISSING"]) == ["MISSING"]

