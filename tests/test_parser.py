import pytest
from parse_weather import parse_weather_data, normalize_temperature, get_station_region

def test_normalize_temperature():
    assert normalize_temperature("25") == 25.0
    assert normalize_temperature("25.5") == 25.5
    assert normalize_temperature("invalid") is None
    assert normalize_temperature(None) is None

def test_get_station_region_east_coast_subregions():
    assert get_station_region("宜蘭測站", 24.75, 121.75) == "東北部地區"
    assert get_station_region("花蓮測站", 23.98, 121.60) == "東部地區"
    assert get_station_region("臺東測站", 22.76, 121.15) == "東南部地區"

def test_parse_cwa_7day_forecast_for_matching_location():
    from parse_weather import parse_cwa_7day_forecast

    cwa_data = {
        "records": {
            "Locations": [{
                "LocationsName": "花蓮縣",
                "Location": [{
                    "LocationName": "花蓮市",
                    "WeatherElement": [
                        {"ElementName": "最高溫度", "Time": [{
                            "StartTime": "2026-09-24 06:00:00",
                            "ElementValue": [{"MaxTemperature": "30"}],
                        }]},
                        {"ElementName": "最低溫度", "Time": [{
                            "StartTime": "2026-09-24 06:00:00",
                            "ElementValue": [{"MinTemperature": "24"}],
                        }]},
                        {"ElementName": "平均相對濕度", "Time": [{
                            "StartTime": "2026-09-24 06:00:00",
                            "ElementValue": [{"RelativeHumidity": "72"}],
                        }]},
                    ],
                }],
            }],
        },
    }

    rows = parse_cwa_7day_forecast(cwa_data, "HUALIEN_001", "花蓮市測站")

    assert len(rows) == 1
    assert rows[0]["station_id"] == "HUALIEN_001"
    assert rows[0]["min_temp"] == 24.0
    assert rows[0]["max_temp"] == 30.0
    assert rows[0]["humidity"] == 72.0

def test_parse_cwa_forecast_handles_iso_dates_and_dash_values():
    from parse_weather import parse_cwa_7day_forecast

    cwa_data = {
        "records": {
            "Locations": [{
                "LocationsName": "臺灣",
                "Location": [{
                    "LocationName": "宜蘭市",
                    "WeatherElement": [
                        {"ElementName": "最高溫度", "Time": [{
                            "StartTime": "2026-09-24T06:00:00+08:00",
                            "ElementValue": [{"MaxTemperature": "-"}],
                        }]},
                        {"ElementName": "最低溫度", "Time": [{
                            "StartTime": "2026-09-24T06:00:00+08:00",
                            "ElementValue": [{"MinTemperature": "23"}],
                        }]},
                        {"ElementName": "12小時降雨機率", "Time": [{
                            "StartTime": "2026-09-24T06:00:00+08:00",
                            "ElementValue": [{"ProbabilityOfPrecipitation": "-"}],
                        }]},
                    ],
                }],
            }],
        },
    }

    rows = parse_cwa_7day_forecast(cwa_data, "YILAN_001", "宜蘭市測站")

    assert len(rows) == 1
    assert rows[0]["forecast_date"] == "2026-09-24"
    assert rows[0]["min_temp"] == 23.0
    assert rows[0]["max_temp"] == -999.0
    assert rows[0]["pop"] == -1

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

