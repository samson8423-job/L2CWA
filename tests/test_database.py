import pytest
import sqlite3
import os
import tempfile
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

