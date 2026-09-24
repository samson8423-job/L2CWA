"""檢查資料庫中的站點數量和重複情況"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "data.db")

if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 檢查AirStations表的總數
    cursor.execute("SELECT COUNT(*) FROM AirStations")
    total = cursor.fetchone()[0]
    print(f"AirStations 表中的總站點數: {total}")
    
    # 檢查是否有重複的station_id（不應該有，因為是PRIMARY KEY）
    cursor.execute("SELECT COUNT(DISTINCT station_id) FROM AirStations")
    unique = cursor.fetchone()[0]
    print(f"不重複的 station_id 數量: {unique}")
    
    # 檢查按地區的分佈
    cursor.execute("SELECT region, COUNT(*) FROM AirStations GROUP BY region ORDER BY COUNT(*) DESC")
    print("\n按地區分佈:")
    for region, count in cursor.fetchall():
        print(f"  {region}: {count}")
    
    # 檢查更新批次日誌
    cursor.execute("SELECT COUNT(*) FROM UpdateLogs")
    log_count = cursor.fetchone()[0]
    print(f"\n更新批次日誌數量: {log_count}")
    
    cursor.execute("SELECT batch_id, update_time, station_count FROM UpdateLogs ORDER BY update_time DESC LIMIT 10")
    print("最新的10次更新:")
    for batch_id, update_time, station_count in cursor.fetchall():
        print(f"  {update_time}: {station_count} 個站點 ({batch_id})")
    
    # 檢查StationHistory表（站點歷史記錄）
    cursor.execute("SELECT COUNT(*) FROM StationHistory")
    hist_count = cursor.fetchone()[0]
    print(f"\nStationHistory 表記錄數: {hist_count}")
    
    cursor.execute("SELECT COUNT(DISTINCT station_id) FROM StationHistory")
    hist_stations = cursor.fetchone()[0]
    print(f"有歷史記錄的站點數: {hist_stations}")
    
    # 檢查AirStationSnapshots表
    cursor.execute("SELECT COUNT(*) FROM AirStationSnapshots")
    snap_count = cursor.fetchone()[0]
    print(f"\nAirStationSnapshots 快照表記錄數: {snap_count}")
    
    conn.close()
    
    print("\n" + "="*50)
    print("建議: 如果 AirStations 數量過多或有異常數據，")
    print("可以執行以下命令清空並重新抓取:")
    print("  python clean_db.py")
else:
    print(f"資料庫不存在: {DB_PATH}")
