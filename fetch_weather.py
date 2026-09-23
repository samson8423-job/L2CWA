import os
import requests
import logging
import urllib3
from dotenv import load_dotenv

# Disable SSL warnings since we are using verify=False for government APIs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

def fetch_weather_data() -> dict:
    """抓取 CWA 天氣預報資料"""
    load_dotenv()
    api_key = os.getenv("CWA_API_KEY")
    url = os.getenv("CWA_API_URL")
    
    if not api_key:
        logger.error("API Key missing in environment variables.")
        raise ValueError("API Key missing. Please check your .env file.")
        
    if not url:
        url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001"
        
    headers = {
        "Authorization": api_key,
        "accept": "application/json",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"抓取 CWA 天氣預報失敗: {e}")
        raise

def fetch_cwa_observations() -> dict:
    """抓取 CWA 自動氣象站即時資料 (O-A0003-001)"""
    load_dotenv()
    api_key = os.getenv("CWA_API_KEY")
    url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0003-001"
    
    if not api_key:
        return {}
        
    headers = {
        "Authorization": api_key,
        "accept": "application/json",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=20, verify=False)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.warning(f"抓取 CWA 即時氣象站失敗: {e}")
        
    return {}

def fetch_airbox_data() -> dict:
    """抓取開放空氣盒子 (AirBox) 即時觀測資料"""
    url = "https://pm25.lass-net.org/data/last-all-airbox.json"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.warning(f"抓取空氣盒子開放資料失敗: {e}")
        
    return {}

def fetch_epa_data() -> dict:
    """抓取開放環保署 (EPA) 測站即時觀測資料"""
    url = "https://pm25.lass-net.org/data/last-all-epa.json"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.warning(f"抓取環保署開放資料失敗: {e}")
        
    return {}

def fetch_cwa_7day_forecast() -> dict:
    """抓取 CWA 全台各縣市未來 1 週天氣預報 (F-D0047-091)"""
    load_dotenv()
    api_key = os.getenv("CWA_API_KEY")
    if not api_key:
        return {}
        
    url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-091"
    headers = {
        "Authorization": api_key,
        "accept": "application/json",
    }
    try:
        response = requests.get(url, headers=headers, timeout=20, verify=False)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.warning(f"抓取 CWA 一週預報失敗: {e}")
        
    return {}


