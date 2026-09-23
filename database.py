import sqlite3
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "data.db")

def init_db():
    """初始化 SQLite 資料庫與資料表"""
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
        
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 既有預報表（保持相容）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS TemperatureForecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                regionName TEXT NOT NULL,
                dataDate TEXT NOT NULL,
                min REAL NOT NULL,
                max REAL NOT NULL,
                UNIQUE(regionName, dataDate)
            )
        ''')
        
        # 空氣盒子站點即時表 (PM2.5、溫度、濕度、座標)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS AirStations (
                station_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                station_type TEXT DEFAULT '空氣盒子觀測點',
                pm25 REAL NOT NULL,
                temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                status TEXT DEFAULT 'active',
                updated_at TEXT NOT NULL
            )
        ''')
        
        # 測站 24 小時歷史時序表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS StationHistory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                station_id TEXT NOT NULL,
                record_time TEXT NOT NULL,
                pm25 REAL NOT NULL,
                temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                UNIQUE(station_id, record_time)
            )
        ''')
        
        conn.commit()
        logger.info("資料庫結構初始化成功")
    except sqlite3.Error as e:
        logger.error(f"資料庫初始化失敗: {e}")
        raise
    finally:
        if conn:
            conn.close()

def insert_air_stations(stations: list[dict]):
    """新增或更新空氣盒子測站資料"""
    if not stations:
        return 0
        
    inserted = 0
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for s in stations:
            cursor.execute('''
                INSERT INTO AirStations (
                    station_id, name, lat, lon, station_type, 
                    pm25, temperature, humidity, status, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(station_id) DO UPDATE SET
                    name = excluded.name,
                    lat = excluded.lat,
                    lon = excluded.lon,
                    station_type = excluded.station_type,
                    pm25 = excluded.pm25,
                    temperature = excluded.temperature,
                    humidity = excluded.humidity,
                    status = excluded.status,
                    updated_at = excluded.updated_at
            ''', (
                s['station_id'], s['name'], s['lat'], s['lon'], 
                s.get('station_type', '空氣盒子觀測點'),
                s['pm25'], s['temperature'], s['humidity'],
                s.get('status', 'active'), s['updated_at']
            ))
            
            # 若有歷史數據一併存入
            history = s.get('history', [])
            for h in history:
                cursor.execute('''
                    INSERT INTO StationHistory (station_id, record_time, pm25, temperature, humidity)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(station_id, record_time) DO UPDATE SET
                        pm25 = excluded.pm25,
                        temperature = excluded.temperature,
                        humidity = excluded.humidity
                ''', (s['station_id'], h['time'], h['pm25'], h['temperature'], h['humidity']))
                
            inserted += 1
            
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"更新站點資料時發生錯誤: {e}")
        raise
    finally:
        if conn:
            conn.close()
            
    return inserted

def get_air_stations(station_type=None, include_offline=False):
    """查詢測站列表"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM AirStations WHERE 1=1'
        params = []
        
        if not include_offline:
            query += " AND status != 'offline'"
            
        if station_type and station_type != 'All':
            query += " AND station_type = ?"
            params.append(station_type)
            
        cursor.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]
        return rows
    except sqlite3.Error as e:
        logger.error(f"查詢站點失敗: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_station_history(station_id):
    """取得指定站點的 24 小時歷史紀錄"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT record_time, pm25, temperature, humidity 
            FROM StationHistory 
            WHERE station_id = ? 
            ORDER BY record_time ASC
        ''', (station_id,))
        rows = [dict(row) for row in cursor.fetchall()]
        return rows
    except sqlite3.Error as e:
        logger.error(f"查詢站點時序失敗: {e}")
        return []
    finally:
        if conn:
            conn.close()

# 保持既有函式相容性
def insert_forecasts(rows):
    if not rows: return 0
    inserted = 0
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        for row in rows:
            cursor.execute('''
                INSERT INTO TemperatureForecasts (regionName, dataDate, min, max)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(regionName, dataDate) DO UPDATE SET
                    min = excluded.min, max = excluded.max;
            ''', (row['regionName'], row['dataDate'], row['min'], row['max']))
            inserted += 1
        conn.commit()
    finally:
        if conn: conn.close()
    return inserted

def get_regions():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT regionName FROM TemperatureForecasts ORDER BY regionName')
        return [row[0] for row in cursor.fetchall()]
    finally:
        if conn: conn.close()

def get_forecasts(region_name=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if region_name:
            cursor.execute('SELECT * FROM TemperatureForecasts WHERE regionName = ? ORDER BY dataDate', (region_name,))
        else:
            cursor.execute('SELECT * FROM TemperatureForecasts ORDER BY dataDate')
        return [dict(row) for row in cursor.fetchall()]
    finally:
        if conn: conn.close()
