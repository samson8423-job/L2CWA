import pytest
import requests
from unittest.mock import patch
from fetch_weather import fetch_weather_data
import os

@patch('fetch_weather.requests.get')
@patch.dict(os.environ, {"CWA_API_KEY": "test_key"})
def test_fetch_weather_success(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"success": "true"}
    
    result = fetch_weather_data()
    assert result == {"success": "true"}
    mock_get.assert_called_once()

@patch('fetch_weather.requests.get')
@patch.dict(os.environ, {"CWA_API_KEY": "test_key"})
def test_fetch_weather_timeout(mock_get):
    mock_get.side_effect = requests.Timeout
    
    with pytest.raises(requests.Timeout):
        fetch_weather_data()

@patch('fetch_weather.load_dotenv')
@patch.dict(os.environ, {"CWA_API_KEY": ""}, clear=True)
def test_fetch_weather_no_key(mock_load_dotenv):
    with pytest.raises(ValueError):
        fetch_weather_data()
