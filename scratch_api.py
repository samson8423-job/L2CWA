import os
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("CWA_API_KEY")
url = os.getenv("CWA_API_URL")

headers = {"Authorization": api_key, "accept": "application/json"}
res = requests.get(url, headers=headers, verify=False)
data = res.json()

locations = [loc["locationName"] for loc in data["records"]["location"]]
print("Locations:", locations)
