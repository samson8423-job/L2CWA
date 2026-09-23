# Taiwan Weather Forecast Dashboard

這是一個利用中央氣象署 (CWA) Open Data API 抓取並顯示台灣區域天氣預報的 Dashboard。

## Installation

建議使用 Python 虛擬環境：

Windows：
```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux：
```bash
python -m venv .venv
source .venv/bin/activate
```

安裝依賴套件：
```bash
pip install -r requirements.txt
```

## Environment

1. 將 `.env.example` 複製一份並重新命名為 `.env`。
2. 填入您的 CWA API Key：

```env
CWA_API_KEY=你的API_KEY
CWA_API_URL=https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001
```

> [!WARNING]
> 請勿將真實的 `.env` 檔案上傳至 GitHub。它已經被加入 `.gitignore`。

## Run

執行 Streamlit 應用程式：

```bash
streamlit run app.py
```

瀏覽器會自動開啟 `http://localhost:8501`。
在畫面上點擊「更新 CWA 資料」即可向 API 請求資料並顯示。

## Test

執行單元測試與語法檢查：

```bash
python -m compileall .
pytest -q
```

## Project Structure

- `app.py`: Streamlit 應用程式進入點與介面
- `fetch_weather.py`: 負責與 CWA API 溝通
- `parse_weather.py`: 處理與清洗 JSON 資料
- `database.py`: SQLite3 資料庫操作 (儲存於 `data/data.db`)
- `tests/`: 包含 Parser, Database 及 API Fetch 的單元測試
