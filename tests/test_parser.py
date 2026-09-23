import pytest
from parse_weather import parse_weather_data, normalize_temperature

def test_normalize_temperature():
    assert normalize_temperature("25") == 25.0
    assert normalize_temperature("25.5") == 25.5
    assert normalize_temperature("invalid") is None
    assert normalize_temperature(None) is None

def test_parse_weather_data_valid():
    sample_data = {
        "records": {
            "location": [
                {
                    "locationName": "臺北市",
                    "weatherElement": [
                        {
                            "elementName": "MinT",
                            "time": [
                                {
                                    "startTime": "2026-04-14 06:00:00",
                                    "parameter": {"parameterName": "20"}
                                }
                            ]
                        },
                        {
                            "elementName": "MaxT",
                            "time": [
                                {
                                    "startTime": "2026-04-14 06:00:00",
                                    "parameter": {"parameterName": "26"}
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }
    
    result = parse_weather_data(sample_data)
    assert len(result) == 1
    assert result[0]["regionName"] == "北部地區"
    assert result[0]["dataDate"] == "2026-04-14"
    assert result[0]["min"] == 20.0
    assert result[0]["max"] == 26.0

def test_parse_weather_data_invalid():
    assert parse_weather_data({}) == []
    assert parse_weather_data({"records": {}}) == []
    
def test_parse_weather_data_missing_temp():
    sample_data = {
        "records": {
            "location": [
                {
                    "locationName": "臺北市",
                    "weatherElement": []
                }
            ]
        }
    }
    assert parse_weather_data(sample_data) == []

def test_parse_airbox_data():
    from parse_weather import parse_airbox_data
    mock_airbox = {
        "feeds": [
            {
                "device_id": "74DA38F7C64C",
                "name": "測試國小",
                "gps_lat": 24.97,
                "gps_lon": 121.39,
                "s_d0": 15.0,
                "s_t0": 28.5,
                "s_h0": 60.0
            }
        ]
    }
    stations = parse_airbox_data(mock_airbox)
    assert len(stations) >= 1
    # 應包含圖片指定站點 AAA2 以及 mock 測站
    ids = [s["station_id"] for s in stations]
    assert "AAA2" in ids
    assert "74DA38F7C64C" in ids

