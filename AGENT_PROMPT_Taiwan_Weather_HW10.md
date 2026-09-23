# HW10｜Taiwan Weather & Air Quality (EdiGreen 空氣盒子) --- Antigravity Agent Implementation Prompt

> **使用方式**
>
> 這份 Markdown 是給 **Antigravity / coding agent**
> 直接閱讀與執行的專案規格。 請把本檔案放在專案根目錄，例如
> `AGENT_PROMPT.md`，然後讓 Agent 讀取本檔案並自行完成實作、測試與修正。
>
> **重要安全要求：API Key 絕對不可寫死在 Python、Streamlit、README、Git
> history 或前端程式碼中。** 所有秘密資訊一律由 `.env` 提供，並且 `.env`
> 必須加入 `.gitignore`。

------------------------------------------------------------------------

## 0. 你的角色

你是一個可以直接操作目前專案資料夾的 **Senior Python Full-Stack / Data
Engineering Coding Agent**。

你的任務不是只提供程式碼範例，而是：

1.  先檢查目前專案資料夾。
2.  理解現有檔案與環境。
3.  建立或修改完整可執行的專案。
4.  安裝/檢查必要 dependencies。
5.  撰寫測試。
6.  實際執行 Python 程式與 Streamlit App。
7.  遇到錯誤時自行 debug、修改、重新執行。
8.  最後確認專案可以由另一個人依照 README 啟動。
9.  不要只停留在「產生程式碼」，必須以「可以執行」為完成標準。

如果專案裡已經有程式碼，**先理解再修改，不要無條件覆蓋現有實作**。

------------------------------------------------------------------------

# 1. 作業目標

完成一個符合 **EdiGreen 空氣盒子（AirBox）** 風格的：

> **Taiwan Weather & Air Quality Monitor｜台灣微型氣象與空氣品質監測 Dashboard**

使用：

-   CWA / 中央氣象署 Open Data API 與 LASS / AirBox 開放資料
-   JSON
-   Python
-   SQLite
-   Streamlit
-   pandas
-   requests
-   python-dotenv
-   Folium / streamlit-folium（滿版台灣即時地圖）
-   pytest（測試）

建立一個可以：

> **取得氣象與空氣品質 API → 解析即時站點資料（PM2.5、溫度、濕度、座標、時序趨勢） → 儲存 SQLite →
> Streamlit 空氣盒子風格介面 → 側邊欄控制（微粒子標準、站點類型、風力線、離線裝置） → 滿版台灣地圖視覺化（含站點色階、詳細 Popup 圖表、左下角微粒色階與右下角觀測站圖例）**

的完整 Web App。

最終使用者應該可以在瀏覽器開啟 Streamlit：

``` text
http://localhost:8501
```

並看到與範例網站完全一致的 EdiGreen 空氣盒子風格 Dashboard。

------------------------------------------------------------------------

# 2. 作業要求總覽

主要分成以下核心功能：

## Part 1 --- 資料整合與 API（PM2.5、溫度、濕度、座標）
- 整合微型氣象與環境部/空氣盒子開放資料（支援 CWA 自動氣象觀測 O-A0003-001 或 LASS/AirBox 開放資料）
- 取得即時測站站名、經緯度座標、PM2.5 (μg/m³)、溫度 (°C)、相對濕度 (%) 與更新時間
- 支援過去 24 小時時序趨勢（PM2.5 折線圖、溫度黃色面積與濕度青藍色面積圖）

## Part 2 --- SQLite 資料庫
- 儲存測站基本資料、即時讀數與 24 小時時序數據
- 具備 upsert 與防重複機制

## Part 3 --- EdiGreen 空氣盒子風格前端介面
- **側邊欄（Sidebar）**：
  - EdiGreen 空氣盒子 Logo 與標題
  - 管理者登入 / 語言切換選單（繁體中文）
  - 「偵測站點顯示」控制面版：
    - 懸浮微粒子標準：[TW] [UK AQI]
    - 偵測站點：[Station] [ADF] 等
    - 風力線：OFF / ON 切換開關
    - 顯示離線裝置：OFF / ON 切換開關
  - 「工具」展開區塊
  - 「🔄 更新即時資料」按鈕
- **滿版互動地圖（Main Map）**：
  - 台灣全島測站地圖
  - 依 PM2.5 濃度顯示對應顏色之標記（Marker / CircleMarker）
  - **點擊站點 Popup 資訊視窗**：
    - 站點名稱與經緯度（如：`AAA2 24.111°N / 120.659°E`）
    - 即時數據：`Pm2.5 : X μg/m³`、`溫度 : XX°C, 濕度 : XX%`
    - PM2.5 過去 24 小時時序折線圖
    - 溫度與濕度過去 24 小時面積/雙曲線時序圖
    - 最後更新時間
  - **地圖左下角**：PM2.5 色階圖例標籤（`<15` 綠色、`35` 黃色、`54` 橘色、`150` 紅色、`250` 紫色、`>251` 褐紅色，單位 `μg/m³`）
  - **地圖右下角**：站點類別圖例（空氣盒子觀測點、環保署觀測站、資料異於周圍環境、機器需檢修、開放資料觀測站）

## Part 1 --- 取得 CWA API 資料（20%）

使用 CWA Open Data API 取得台灣區域的天氣預報 JSON。

需求：

-   使用 Python `requests`
-   API Key 從 `.env` 讀取
-   不得把 API Key 寫死
-   使用 `json` / Python dict 處理 JSON
-   能處理 API HTTP error / timeout / invalid JSON
-   建議保留原始 API response 的能力，方便 debug

作業指定資料集：

``` text
F-A0010-001
```

API base：

``` text
https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-A0010-001
```

CWA API 官方文件：

``` text
https://opendata.cwa.gov.tw/dataset/forecast/F-A0010-001
https://opendata.cwa.gov.tw/devManual/insrtuction

USE CWA O-A0003-001 is better
```

**注意：**

Agent 執行時應再次確認 CWA API 現行 JSON schema。

不要盲目假設 JSON 永遠固定。

------------------------------------------------------------------------

# 3. `.env` 與秘密資訊

專案根目錄建立：

``` text
.env
```

範例：

``` env
CWA_API_KEY=YOUR_CWA_API_KEY
CWA_API_URL=https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-A0010-001
```

如果實際 API 認證欄位需要使用其他命名，也可以在程式內統一處理，但 `.env`
至少應有：

``` text
CWA_API_KEY
```

推薦使用：

``` python
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("CWA_API_KEY")
```

HTTP request 建議使用 Header：

``` python
headers = {
    "Authorization": api_key,
    "accept": "application/json",
}
```

如果 CWA API 當前文件要求不同方式，請以官方文件為準。

## 絕對禁止

不要出現：

``` python
CWA_API_KEY = "CWA-xxxxxxxxxxxxxxxx"
```

也不要：

``` python
url = "...?Authorization=CWA-xxxxxxxx"
```

不要把真實 API Key 寫入：

-   `.py`
-   `.md`
-   `.json`
-   `.yaml`
-   `.yml`
-   `.toml`
-   `.ipynb`
-   Streamlit code
-   frontend JavaScript
-   Git commit

------------------------------------------------------------------------

# 4. `.gitignore`

至少建立：

``` gitignore
.env
.env.*
!.env.example

__pycache__/
*.py[cod]

.venv/
venv/
env/

.pytest_cache/
.coverage

data/*.db
*.db

.streamlit/secrets.toml

.DS_Store
```

建立：

``` text
.env.example
```

內容只能放 placeholder：

``` env
CWA_API_KEY=YOUR_CWA_API_KEY
CWA_API_URL=https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-A0010-001
```

------------------------------------------------------------------------

# 5. 建議專案結構

請建立成類似：

``` text
HW10_Weather/
│
├─ app.py
├─ fetch_weather.py
├─ parse_weather.py
├─ database.py
├─ requirements.txt
├─ README.md
├─ AGENT_PROMPT.md
│
├─ .env
├─ .env.example
├─ .gitignore
│
├─ data/
│  └─ data.db
│
├─ tests/
│  ├─ test_parser.py
│  ├─ test_database.py
│  └─ test_fetch.py
│
└─ assets/
   └─ （如需要的圖片/圖示）
```

如果現有專案已有合理結構，可以保留，但必須維持：

-   API
-   parsing
-   database
-   UI

至少有清楚的責任分離。

------------------------------------------------------------------------

# 6. Part 1 --- API Fetch

建立：

``` text
fetch_weather.py
```

建議至少提供：

``` python
def fetch_weather_data() -> dict:
    ...
```

功能：

1.  從 `.env` 讀取 API Key。
2.  取得 API URL。
3.  發送 GET request。
4.  timeout 建議 30 秒。
5.  `response.raise_for_status()`
6.  JSON decode。
7.  回傳 Python dict。
8.  發生錯誤時提供可理解的錯誤訊息。

建議處理：

``` text
requests.Timeout
requests.RequestException
JSONDecodeError
API Key missing
API response malformed
```

不要在 exception 中洩漏 API Key。

------------------------------------------------------------------------

# 7. Part 2 --- JSON Parsing

建立：

``` text
parse_weather.py
```

核心目標：

從 CWA JSON：

``` text
records
└── locations / location
    └── location
        └── weatherElement
            ├── MinT
            └── MaxT
```

實際欄位名稱與 nesting 必須以 API 現行回傳資料為準。

需要抽出：

``` text
regionName
dataDate
min
max
```

最後整理成：

``` python
[
    {
        "regionName": "北部地區",
        "dataDate": "2026-04-14",
        "min": 18,
        "max": 26,
    },
    ...
]
```

------------------------------------------------------------------------

# 8. 六大區域

作業圖片要求：

``` text
北部地區
中部地區
南部地區
東部地區
東北部地區
東南部地區
```

優先支援這六個名稱。

但請注意：

**不要假設 API 永遠一定回傳這六個名稱。**

Agent 執行時：

1.  先實際呼叫 API。
2.  印出 / 檢查 `records`。
3.  找出目前 API 實際提供的區域。
4.  建立 region mapping。
5.  如果 API 的區域名稱與作業圖片不同，建立明確
    mapping，而不是偷偷丟資料。

例如：

``` python
REGION_MAPPING = {
    "北部地區": "...",
    "中部地區": "...",
}
```

如果 API 實際只提供部分區域，也要：

-   在 README 說明
-   UI 清楚顯示
-   不要假造不存在的資料

------------------------------------------------------------------------

# 9. Parser 必須容錯

JSON parser 不可以只寫成：

``` python
data["records"]["location"][0]["weatherElement"][0]["time"][0]
```

然後假設永遠成功。

至少需要：

-   missing key handling
-   empty list handling
-   unexpected element handling
-   temperature conversion
-   invalid date handling
-   duplicated records handling

推薦：

``` python
def parse_weather_data(data: dict) -> list[dict]:
    ...
```

並且加入：

``` python
def normalize_temperature(value):
    ...
```

------------------------------------------------------------------------

# 10. 日期格式

Database 與 UI 建議使用：

``` text
YYYY-MM-DD
```

例如：

``` text
2026-04-14
```

Python：

``` python
date.fromisoformat(...)
```

避免把日期全部當成一般字串處理。

------------------------------------------------------------------------

# 11. Part 3 --- SQLite Database

建立：

``` text
database.py
```

資料庫：

``` text
data/data.db
```

Table：

``` sql
CREATE TABLE IF NOT EXISTS TemperatureForecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    regionName TEXT NOT NULL,
    dataDate TEXT NOT NULL,
    min REAL NOT NULL,
    max REAL NOT NULL,
    UNIQUE(regionName, dataDate)
);
```

如果實際設計需要其他欄位可以增加，但至少必須包含：

``` text
id
regionName
dataDate
min
max
```

------------------------------------------------------------------------

# 12. Database Functions

至少實作：

``` python
def init_db():
    ...

def insert_forecasts(rows):
    ...

def get_regions():
    ...

def get_forecasts(region_name=None):
    ...

def get_forecasts_by_date(...):
    ...
```

使用：

``` python
sqlite3
```

不要依賴 ORM。

------------------------------------------------------------------------

# 13. SQLite Upsert

重複執行 API fetch 時，不應產生大量 duplicate data。

建議：

``` sql
INSERT INTO TemperatureForecasts (...)
VALUES (...)
ON CONFLICT(regionName, dataDate)
DO UPDATE SET
    min = excluded.min,
    max = excluded.max;
```

如果 SQLite 版本或 schema 不適合，使用等價安全方法。

------------------------------------------------------------------------

# 14. 必須能查詢

至少支援：

## 查詢所有區域

``` sql
SELECT DISTINCT regionName
FROM TemperatureForecasts
ORDER BY regionName;
```

## 查詢指定區域

例如：

``` sql
SELECT *
FROM TemperatureForecasts
WHERE regionName = '中部地區'
ORDER BY dataDate;
```

------------------------------------------------------------------------

# 15. Part 4 --- Streamlit Web App（40%）

建立：

``` text
app.py
```

啟動：

``` bash
streamlit run app.py
```

------------------------------------------------------------------------

# 16. Streamlit UI

畫面名稱：

``` text
Taiwan Weather Forecast
```

或：

``` text
台灣天氣預報
```

可以採用中英雙語。

------------------------------------------------------------------------

# 17. UI 必須有 Region Dropdown

例如：

``` text
Select Region
[ 中部地區 ▼ ]
```

選項：

``` text
北部地區
中部地區
南部地區
東部地區
東北部地區
東南部地區
```

但 dropdown 必須根據 DB 中實際存在的 region 動態產生。

不要硬編一個永遠存在的資料集合。

------------------------------------------------------------------------

# 18. 選擇區域後顯示

## A. Temperature Line Chart

需要顯示：

``` text
MaxT
MinT
```

X：

``` text
Date
```

Y：

``` text
Temperature (°C)
```

例如：

``` text
Temperature Forecast - 中部地區
```

------------------------------------------------------------------------

# 19. Table

顯示：

  Date           MinT   MaxT
  ------------ ------ ------
  2026-04-14       20     30
  2026-04-15       21     31
  2026-04-16       22     32

可以使用：

``` python
st.dataframe(...)
```

或：

``` python
st.table(...)
```

------------------------------------------------------------------------

# 20. KPI / Summary

建議在圖表上方加入：

``` text
最低溫
最高溫
平均最低溫
平均最高溫
```

例如：

``` text
最低溫：20°C
最高溫：32°C
```

這不是作業圖片的硬性必要項目，但可以提升 Dashboard 完整度。

------------------------------------------------------------------------

# 21. API 更新功能

建議加入按鈕：

``` text
🔄 更新 CWA 資料
```

按下後：

1.  呼叫 API
2.  Parse JSON
3.  Validate
4.  Upsert SQLite
5.  顯示成功筆數
6.  Refresh UI

例如：

``` text
成功更新 42 筆天氣資料
```

如果失敗：

``` text
資料更新失敗：...
```

不要顯示 API Key。

------------------------------------------------------------------------

# 22. Cache

可以使用 Streamlit cache：

``` python
@st.cache_data
```

但必須避免 cache 讓「更新 CWA 資料」按鈕失效。

推薦設計：

-   API fetch 可以 cache 短時間
-   更新按鈕成功後 `st.cache_data.clear()`
-   DB query 可以依實際情況 cache

------------------------------------------------------------------------

# 23. Loading / Error UX

Streamlit 不應該因為 API 掛掉直接白屏。

至少處理：

``` text
API Key 未設定
API timeout
API 401 / 403
API 404
API 500
JSON 格式錯誤
SQLite error
目前沒有資料
```

UI 使用：

``` python
st.error(...)
st.warning(...)
st.success(...)
st.info(...)
```

------------------------------------------------------------------------

# 24. Part 5 --- Taiwan Map（Optional / 加分）

作業圖片提供：

> Folium + Streamlit

建立台灣地圖。

推薦：

``` text
folium
streamlit-folium
```

地圖至少：

-   顯示台灣
-   顯示六大區域 marker
-   Marker 顯示：
    -   區域名稱
    -   日期
    -   Min
    -   Max

------------------------------------------------------------------------

# 25. Map 溫度顏色

依照作業圖片：

``` text
< 20°C       藍色
20–25°C      綠色
25–30°C      黃色
> 30°C       紅色
```

注意：

這個顏色分類應套用到「平均溫度」或明確定義的區域溫度指標。

推薦：

``` python
avg_temp = (min_temp + max_temp) / 2
```

然後：

``` text
avg < 20      blue
20 <= avg <25 green
25 <= avg <=30 yellow
avg > 30      red
```

UI 必須說明使用哪一個溫度作為 marker 顏色依據。

------------------------------------------------------------------------

# 26. 地圖座標

不要為了完成作業亂猜座標。

可以建立：

``` python
REGION_COORDINATES = {
    ...
}
```

座標只需要代表該區域的大致中心位置。

例如：

``` text
北部
中部
南部
東部
東北部
東南部
```

並在程式碼註解說明：

> These are representative regional coordinates for visualization, not
> official administrative boundaries.

------------------------------------------------------------------------

# 27. 地圖不是主要資料來源

地圖上的數據必須來自 SQLite / parsed weather data。

不要：

``` text
地圖自己寫死溫度
```

正確：

``` text
CWA API
  ↓
Parser
  ↓
SQLite
  ↓
Streamlit
  ↓
Folium
```

------------------------------------------------------------------------

# 28. 資料流程

完整資料流程必須是：

``` text
CWA Open Data API
        │
        ▼
   requests.get()
        │
        ▼
      JSON
        │
        ▼
 parse_weather.py
        │
        ▼
 normalized records
        │
        ▼
     SQLite
    data.db
        │
        ├───────────────┐
        ▼               ▼
 Streamlit Chart     Streamlit Table
        │
        ▼
   Folium Map
```

------------------------------------------------------------------------

# 29. 不要讓 UI 直接解析 API JSON

錯誤架構：

``` text
app.py
  ↓
requests
  ↓
巨大 JSON parsing
  ↓
畫圖
```

推薦架構：

``` text
fetch_weather.py
       ↓
parse_weather.py
       ↓
database.py
       ↓
app.py
```

這樣方便測試與維護。

------------------------------------------------------------------------

# 30. Requirements

至少需要：

``` text
requests
python-dotenv
pandas
streamlit
folium
streamlit-folium
pytest
```

如果實際使用其他套件，再加入。

建立：

``` text
requirements.txt
```

例如：

``` text
requests
python-dotenv
pandas
streamlit
folium
streamlit-folium
pytest
```

不要固定非常舊的版本。

如果有必要，可以使用合理的 minimum version。

------------------------------------------------------------------------

# 31. 測試

建立：

``` text
tests/
```

至少測：

## Parser

測試：

``` text
valid JSON → expected records
```

測試：

``` text
missing records
empty location
missing temperature
```

------------------------------------------------------------------------

## Database

測試：

``` text
init DB
insert
query
upsert
```

最好使用：

``` text
SQLite :memory:
```

避免測試污染正式：

``` text
data/data.db
```

------------------------------------------------------------------------

## API

不要讓 unit test 每次都真的打 CWA API。

使用 mock。

例如：

``` python
unittest.mock
```

或：

``` text
pytest monkeypatch
```

測試：

``` text
200
401
500
timeout
invalid JSON
```

------------------------------------------------------------------------

# 32. 測試指令

Agent 必須實際執行：

``` bash
pytest -q
```

如果有 lint / formatting：

``` bash
python -m compileall .
```

至少執行：

``` bash
python -m compileall .
pytest -q
```

------------------------------------------------------------------------

# 33. 啟動測試

Agent 必須實際嘗試：

``` bash
streamlit run app.py
```

確認：

-   app 能啟動
-   沒有 import error
-   沒有 syntax error
-   沒有 database error
-   UI 可以 render

如果 Agent 環境無法直接開瀏覽器，至少確認 Streamlit process
能成功啟動並監聽 port。

------------------------------------------------------------------------

# 34. README

建立：

``` text
README.md
```

README 必須包含：

## Installation

``` bash
python -m venv .venv
```

Windows：

``` bash
.venv\Scripts\activate
```

macOS/Linux：

``` bash
source .venv/bin/activate
```

安裝：

``` bash
pip install -r requirements.txt
```

------------------------------------------------------------------------

## Environment

複製：

``` text
.env.example
```

成：

``` text
.env
```

填入：

``` env
CWA_API_KEY=你的API_KEY
```

提醒：

``` text
不要把 .env 上傳 GitHub。
```

------------------------------------------------------------------------

## Run

``` bash
streamlit run app.py
```

------------------------------------------------------------------------

## Test

``` bash
pytest -q
```

------------------------------------------------------------------------

# 35. API Key 安全檢查

完成後 Agent 必須搜尋整個 repository：

``` text
CWA-
Authorization=
CWA_API_KEY
```

確認沒有真實 key 出現在 source code。

如果找到：

-   立即移除
-   改成環境變數
-   檢查 `.gitignore`

------------------------------------------------------------------------

# 36. Git 安全

確認：

``` bash
git status
```

如果是 Git repository：

`.env` 不應出現在 tracked files。

如果 `.env` 已經被追蹤：

``` bash
git rm --cached .env
```

但不要破壞使用者既有 Git history。

------------------------------------------------------------------------

# 37. Data Validation

API 資料進 SQLite 前要驗證：

``` text
regionName != empty
dataDate is valid date
min is numeric
max is numeric
min <= max
```

若資料異常：

不要讓整個 application crash。

可以：

``` text
skip invalid record
log warning
continue
```

------------------------------------------------------------------------

# 38. Logging

建議使用 Python `logging`：

``` python
import logging

logger = logging.getLogger(__name__)
```

至少記錄：

``` text
API request started
API request succeeded
number of records received
number of records parsed
number of records inserted
database errors
```

不要 log：

``` text
API KEY
Authorization header
.env contents
```

------------------------------------------------------------------------

# 39. UI 設計方向

整體風格參考作業圖片：

``` text
┌──────────────────────────────────────────────┐
│ Taiwan Weather Forecast                      │
│ 台灣天氣預報                                 │
├──────────────────────────────────────────────┤
│ Select Region [ 中部地區 ▼ ]                 │
├──────────────┬──────────────┬────────────────┤
│ Min Temp     │ Max Temp     │ Avg Temp       │
│ 20°C         │ 32°C         │ 26°C           │
├──────────────────────────────────────────────┤
│ Temperature Forecast                         │
│                                              │
│       MaxT ────────────────                  │
│                                              │
│       MinT ────────────────                  │
│                                              │
├───────────────────────────┬──────────────────┤
│ Forecast Table             │ Taiwan Map      │
│ Date MinT MaxT             │                  │
│ ...                        │     🇹🇼          │
└───────────────────────────┴──────────────────┘
```

不要求 100% 複製圖片。

重點是：

-   清楚
-   可操作
-   資料正確
-   Chart
-   Table
-   Map
-   Update button

------------------------------------------------------------------------

# 40. 參考網站

使用者提供的成果參考：

``` text
https://airbox.edimaxcloud.com/
```

這個網站主要作為：

-   Web dashboard UX
-   資料呈現方式
-   互動式圖表
-   Dashboard layout

的參考。

**不要複製其程式碼、商標、品牌素材或私有內容。**

如果執行環境無法連線到網站：

> 不要因此停止工作。

直接依照本文件與作業圖片完成。

------------------------------------------------------------------------

# 41. 官方 CWA 資料參考

CWA Open Data：

``` text
https://opendata.cwa.gov.tw/
```

指定資料集：

``` text
https://opendata.cwa.gov.tw/dataset/forecast/F-A0010-001
```

CWA API 使用說明：

``` text
https://opendata.cwa.gov.tw/devManual/insrtuction
```

Agent 應優先以官方文件與「實際 API response」判斷
schema，不要依賴第三方部落格的舊範例。

------------------------------------------------------------------------

# 42. 非常重要：不要假造資料

如果 CWA API 實際回傳：

``` text
A
B
C
```

而作業圖片寫：

``` text
A
B
C
D
E
F
```

不能自行製造：

``` text
D
E
F
```

必須：

1.  查官方 API。
2.  確認現行 schema。
3.  做合理 mapping。
4.  若資料不存在，在 README 說明。

------------------------------------------------------------------------

# 43. Agent 執行順序

請嚴格按照以下流程：

## Step 1

檢查：

``` bash
pwd
ls
```

Windows 可以使用：

``` powershell
Get-Location
Get-ChildItem
```

------------------------------------------------------------------------

## Step 2

檢查現有：

``` text
Python version
pip
existing source files
requirements
.gitignore
.env
```

------------------------------------------------------------------------

## Step 3

讀取現有程式碼。

如果已存在：

``` text
app.py
fetch_weather.py
database.py
```

先理解再修改。

------------------------------------------------------------------------

## Step 4

確認 CWA API。

實際執行一次 API request。

**API Key 必須來自 `.env`。**

不要要求使用者把 API Key 貼到聊天視窗。

如果 `.env` 尚未存在：

建立 `.env.example`，並在需要真正 API key 才能繼續的地方清楚告知：

``` text
Please create .env and set CWA_API_KEY.
```

不要要求使用者把 secret 傳給 Agent。

------------------------------------------------------------------------

## Step 5

解析實際 JSON。

印出：

``` text
top-level keys
records structure
region names
weather element names
date range
```

注意：

**不要印出 Authorization header 或 API Key。**

------------------------------------------------------------------------

## Step 6

完成 parser。

------------------------------------------------------------------------

## Step 7

完成 SQLite。

------------------------------------------------------------------------

## Step 8

完成 Streamlit。

------------------------------------------------------------------------

## Step 9

完成 Folium map。

------------------------------------------------------------------------

## Step 10

加入 tests。

------------------------------------------------------------------------

## Step 11

執行：

``` bash
python -m compileall .
pytest -q
```

------------------------------------------------------------------------

## Step 12

執行：

``` bash
streamlit run app.py
```

確認 app 啟動。

------------------------------------------------------------------------

## Step 13

如果有 error：

> 自己分析 traceback → 修改 → 再跑。

不要在遇到第一個 error 就停止。

------------------------------------------------------------------------

## Step 14

最後再次確認：

``` text
.env
.gitignore
.env.example
README.md
requirements.txt
tests/
data/
```

------------------------------------------------------------------------

# 44. Definition of Done

只有符合以下條件才算完成：

### API

-   [ ] CWA API 可以成功取得資料
-   [ ] API Key 使用 `.env`
-   [ ] 沒有 hardcoded secret
-   [ ] timeout / HTTP error 有處理

### JSON

-   [ ] 可以解析實際 API response
-   [ ] 可以取得 region
-   [ ] 可以取得日期
-   [ ] 可以取得 MinT
-   [ ] 可以取得 MaxT
-   [ ] parser 有 unit tests

### SQLite

-   [ ] `data/data.db`
-   [ ] `TemperatureForecasts`
-   [ ] primary key
-   [ ] unique constraint / equivalent duplicate protection
-   [ ] insert/upsert
-   [ ] query

### Streamlit

-   [ ] App 可啟動
-   [ ] Region dropdown
-   [ ] Line chart
-   [ ] Temperature table
-   [ ] Update button
-   [ ] Error handling
-   [ ] loading / status feedback

### Map

-   [ ] Folium map
-   [ ] Taiwan regional markers
-   [ ] marker popup
-   [ ] temperature color legend

### Security

-   [ ] `.env` ignored
-   [ ] `.env.example`
-   [ ] no real API key in source
-   [ ] no API key in logs

### Testing

-   [ ] `python -m compileall .`
-   [ ] `pytest -q`
-   [ ] Streamlit successfully starts

### Documentation

-   [ ] README
-   [ ] installation
-   [ ] `.env` setup
-   [ ] run command
-   [ ] test command
-   [ ] project structure

------------------------------------------------------------------------

# 45. 最後回報格式

完成後，不要只說：

``` text
Done.
```

請用以下格式回報：

``` text
## Implementation Summary

### Created
- app.py
- fetch_weather.py
- parse_weather.py
- database.py
- tests/...
- README.md
- requirements.txt
- .env.example
- .gitignore

### Features
- CWA API integration
- JSON parsing
- SQLite storage
- Streamlit dashboard
- Temperature chart
- Forecast table
- Taiwan map
- Region selector
- API refresh

### Validation
- python -m compileall . : PASS/FAIL
- pytest -q : PASS/FAIL
- Streamlit startup : PASS/FAIL

### Security
- API key loaded from .env
- .env ignored by Git
- no hardcoded API key found

### Notes
- Explain any CWA API schema differences.
- Explain any assumptions.
- Explain anything that could not be tested.
```

------------------------------------------------------------------------

# 46. 最重要的 Agent 指令

**不要只是回答我「應該怎麼做」。**

你現在就是負責完成這個作業的 coding agent。

請：

> **Inspect → Plan → Implement → Run → Test → Debug → Verify →
> Document**

直到專案真正可以執行。

如果已有程式碼：

> **Preserve useful existing work and improve it instead of blindly
> replacing it.**

如果遇到問題：

> **先自己嘗試解決，再繼續執行。**

如果 API schema 和這份文件不一致：

> **以 CWA 官方文件 + 實際 API response 為準，並更新 implementation。**

如果沒有 API Key：

> **不要要求使用者把 API Key 貼給你。請使用 `.env`，必要時建立
> `.env.example` 並清楚指出使用者需要自行填入。**

完成標準不是「程式碼看起來正確」。

完成標準是：

> **另一個人拿到專案、建立 `.env`、執行
> `pip install -r requirements.txt`、執行 `streamlit run app.py`
> 後，可以使用 Taiwan Weather Forecast Dashboard。**
