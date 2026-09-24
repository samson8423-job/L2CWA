import sqlite3
import os
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "data.db")

def init_db():
    """初始化 SQLite 資料庫與資料表"""
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
        
    conn = None
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
        
        # 空氣盒子站點即時表 (PM2.5、溫度、濕度、座標、所屬分區)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS AirStations (
                station_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                region TEXT DEFAULT '中部地區',
                station_type TEXT DEFAULT '空氣盒子觀測點',
                pm25 REAL NOT NULL,
                temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                status TEXT DEFAULT 'active',
                updated_at TEXT NOT NULL
            )
        ''')
        
        # 如果舊表缺少 region 欄位，自動擴充
        try:
            cursor.execute("ALTER TABLE AirStations ADD COLUMN region TEXT DEFAULT '中部地區'")
        except sqlite3.OperationalError:
            pass  # 已存在該欄位
        
        # 測站歷史時序表
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
        
        # 即時資料更新快照歷史表（完整記錄每一次同步/更新的資料）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS AirStationSnapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT NOT NULL,
                station_id TEXT NOT NULL,
                name TEXT NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                region TEXT,
                station_type TEXT,
                pm25 REAL NOT NULL,
                temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                status TEXT,
                updated_at TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            )
        ''')
        
        # 更新批次日誌表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS UpdateLogs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT NOT NULL,
                update_time TEXT NOT NULL,
                station_count INTEGER NOT NULL,
                note TEXT
            )
        ''')
        
        # 未來 7 天天氣預報表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS SevenDayForecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                station_id TEXT NOT NULL,
                forecast_date TEXT NOT NULL,
                weekday TEXT NOT NULL,
                weather TEXT NOT NULL,
                min_temp REAL NOT NULL,
                max_temp REAL NOT NULL,
                humidity REAL NOT NULL,
                pop INTEGER NOT NULL,
                description TEXT,
                updated_at TEXT NOT NULL,
                UNIQUE(station_id, forecast_date)
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
    """僅新增或更新有變化的測站，並為變更資料記錄快照。"""
    if not stations:
        return 0

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        changed_stations = []
        for s in stations:
            sid = str(s['station_id'])
            sname = str(s['name'])
            lat = float(s['lat'])
            lon = float(s['lon'])
            region = str(s.get('region', '中部地區'))
            stype = str(s.get('station_type', '空氣盒子觀測點'))
            pm25 = float(s['pm25'])
            temp = float(s['temperature'])
            hum = float(s['humidity'])
            status = str(s.get('status', 'active'))
            up_at = str(s.get('updated_at', now_str))

            cursor.execute('''
                SELECT name, lat, lon, region, station_type, pm25,
                       temperature, humidity, status
                FROM AirStations WHERE station_id = ?
            ''', (sid,))
            previous = cursor.fetchone()
            current = (sname, lat, lon, region, stype, pm25, temp, hum, status)
            if previous == current:
                continue
            changed_stations.append((s, sid, sname, lat, lon, region, stype,
                                     pm25, temp, hum, status, up_at))

        if not changed_stations:
            conn.commit()
            return 0

        batch_id = datetime.now().strftime("BATCH_%Y%m%d_%H%M%S_%f")
        cursor.execute('''
            INSERT INTO UpdateLogs (batch_id, update_time, station_count, note)
            VALUES (?, ?, ?, ?)
        ''', (batch_id, now_str, len(changed_stations),
              f"新增或更新 {len(changed_stations)} 個有變化的測站"))

        for (s, sid, sname, lat, lon, region, stype,
             pm25, temp, hum, status, up_at) in changed_stations:
            cursor.execute('''
                INSERT INTO AirStationSnapshots (
                    batch_id, station_id, name, lat, lon, region, station_type,
                    pm25, temperature, humidity, status, updated_at, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (batch_id, sid, sname, lat, lon, region, stype,
                  pm25, temp, hum, status, up_at, now_str))

            cursor.execute('''
                INSERT INTO AirStations (
                    station_id, name, lat, lon, region, station_type, 
                    pm25, temperature, humidity, status, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(station_id) DO UPDATE SET
                    name = excluded.name,
                    lat = excluded.lat,
                    lon = excluded.lon,
                    region = excluded.region,
                    station_type = excluded.station_type,
                    pm25 = excluded.pm25,
                    temperature = excluded.temperature,
                    humidity = excluded.humidity,
                    status = excluded.status,
                    updated_at = excluded.updated_at
            ''', (sid, sname, lat, lon, region, stype, pm25, temp, hum, status, up_at))

            history = s.get('history', [])
            for h in history:
                r_time = h.get('time') or h.get('record_time') or '00:00'
                cursor.execute('''
                    INSERT INTO StationHistory (station_id, record_time, pm25, temperature, humidity)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(station_id, record_time) DO UPDATE SET
                        pm25 = excluded.pm25,
                        temperature = excluded.temperature,
                        humidity = excluded.humidity
                    WHERE StationHistory.pm25 != excluded.pm25
                       OR StationHistory.temperature != excluded.temperature
                       OR StationHistory.humidity != excluded.humidity
                ''', (sid, r_time, float(h['pm25']), float(h['temperature']), float(h['humidity'])))

        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"更新站點資料時發生錯誤: {e}")
        raise
    finally:
        if conn:
            conn.close()
            
    return len(changed_stations)

def get_air_stations(station_type=None, region=None, include_offline=False):
    """查詢測站列表，支援站點類型與分區（北部、中部、南部、東部、東北、東南、外島）篩選"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM AirStations WHERE 1=1'
        params = []
        
        if not include_offline:
            query += " AND status != 'offline'"
            
        # 若指定特定地區
        if region:
            query += " AND region = ?"
            params.append(region)
            
        # 若指定特定站點類別
        if station_type and station_type not in ['All', '全部', '全台']:
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

def update_station_regions(station_regions: list[tuple[str, str]]):
    """批次更新既有測站的區域分類，不改動即時數值與更新時間"""
    if not station_regions:
        return 0

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.executemany(
            "UPDATE AirStations SET region = ? WHERE station_id = ? AND region != ?",
            [(region, station_id, region) for station_id, region in station_regions],
        )
        updated = cursor.rowcount
        conn.commit()
        return updated
    except sqlite3.Error as e:
        logger.error(f"更新測站區域分類失敗: {e}")
        raise
    finally:
        if conn:
            conn.close()

def get_station_history(station_id):
    """取得指定站點的 24 小時歷史紀錄"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT record_time, record_time AS time, pm25, temperature, humidity 
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

def get_station_histories(station_ids: list[str]):
    """一次查詢多個站點的歷史資料，避免逐站建立資料庫連線。"""
    if not station_ids:
        return {}

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        placeholders = ",".join("?" for _ in station_ids)
        cursor.execute(f'''
            SELECT station_id, record_time, record_time AS time,
                   pm25, temperature, humidity
            FROM StationHistory
            WHERE station_id IN ({placeholders})
            ORDER BY station_id, record_time ASC
        ''', station_ids)
        histories = {str(station_id): [] for station_id in station_ids}
        for row in cursor.fetchall():
            record = dict(row)
            histories[record["station_id"]].append(record)
        return histories
    except sqlite3.Error as e:
        logger.error(f"批次查詢站點時序失敗: {e}")
        return {str(station_id): [] for station_id in station_ids}
    finally:
        if conn:
            conn.close()

def insert_7day_forecasts(forecasts: list[dict]):
    """儲存或更新未來 7 天天氣預報"""
    if not forecasts:
        return 0
    conn = None
    inserted = 0
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        for f in forecasts:
            cursor.execute('''
                INSERT INTO SevenDayForecasts (
                    station_id, forecast_date, weekday, weather, 
                    min_temp, max_temp, humidity, pop, description, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(station_id, forecast_date) DO UPDATE SET
                    weekday = excluded.weekday,
                    weather = excluded.weather,
                    min_temp = excluded.min_temp,
                    max_temp = excluded.max_temp,
                    humidity = excluded.humidity,
                    pop = excluded.pop,
                    description = excluded.description,
                    updated_at = excluded.updated_at
                    WHERE SevenDayForecasts.weekday != excluded.weekday
                       OR SevenDayForecasts.weather != excluded.weather
                       OR SevenDayForecasts.min_temp != excluded.min_temp
                       OR SevenDayForecasts.max_temp != excluded.max_temp
                       OR SevenDayForecasts.humidity != excluded.humidity
                       OR SevenDayForecasts.pop != excluded.pop
                       OR COALESCE(SevenDayForecasts.description, '') != COALESCE(excluded.description, '')
            ''', (
                f['station_id'], f['forecast_date'], f['weekday'], f['weather'],
                f['min_temp'], f['max_temp'], f['humidity'], f['pop'],
                f.get('description', ''), f.get('updated_at', '')
            ))
            inserted += cursor.rowcount
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"儲存一週預報失敗: {e}")
        raise
    finally:
        if conn:
            conn.close()
    return inserted

def get_7day_forecasts(station_id: str):
    """取得特定測站的未來 7 天天氣預報資訊"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM SevenDayForecasts 
            WHERE station_id = ? 
            ORDER BY forecast_date ASC
        ''', (station_id,))
        rows = [dict(row) for row in cursor.fetchall()]
        return rows
    except sqlite3.Error as e:
        logger.error(f"查詢一週預報失敗: {e}")
        return []
    finally:
        if conn:
            conn.close()

def has_7day_forecasts():
    """判斷資料庫是否已有任何七日預報快取"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM SevenDayForecasts)")
        row = cursor.fetchone()
        return bool(row and row[0])
    except sqlite3.Error as e:
        logger.error(f"檢查七日預報資料失敗: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_station_ids_needing_7day_forecasts(station_ids: list[str]):
    """查詢指定測站中缺少目前七日預報日期的站點 ID"""
    if not station_ids:
        return []

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT stations.station_id
            FROM AirStations AS stations
            LEFT JOIN SevenDayForecasts AS forecasts
                ON forecasts.station_id = stations.station_id
            GROUP BY stations.station_id
            HAVING COUNT(DISTINCT CASE
                WHEN forecasts.forecast_date >= ? THEN forecasts.forecast_date
            END) < 7
        """, (date.today().isoformat(),))
        requested_ids = set(station_ids)
        return [row[0] for row in cursor.fetchall() if row[0] in requested_ids]
    except sqlite3.Error as e:
        logger.error(f"查詢缺少七日預報的站點失敗: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_update_logs(limit=10):
    """查詢歷史更新日誌記錄"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM UpdateLogs ORDER BY id DESC LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"查詢更新日誌失敗: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_snapshot_count():
    """取得資料庫中已記錄的即時資料快照總筆數"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM AirStationSnapshots')
        row = cursor.fetchone()
        return row[0] if row else 0
    except sqlite3.Error:
        return 0
    finally:
        if conn:
            conn.close()

# 保持既有函式相容性
def insert_forecasts(rows):
    if not rows: return 0
    inserted = 0
    conn = None
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
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT regionName FROM TemperatureForecasts ORDER BY regionName')
        return [row[0] for row in cursor.fetchall()]
    finally:
        if conn: conn.close()

def get_forecasts(region_name=None):
    conn = None
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
