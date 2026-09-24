import sqlite3

conn = sqlite3.connect("data/data.db")

cursor = conn.cursor()

cursor.execute("SELECT * FROM TemperatureForecasts")

rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()