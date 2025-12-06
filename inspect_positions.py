
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
TARGET_WALLET = os.getenv("TARGET_WALLET")

url = "https://data-api.polymarket.com/positions"
params = {'user': TARGET_WALLET}
headers = {'User-Agent': 'Mozilla/5.0'}

resp = requests.get(url, params=params, headers=headers)
data = resp.json()

if isinstance(data, list) and len(data) > 0:
    print(json.dumps(data[0], indent=2))
else:
    print("No positions found or error:", data)
