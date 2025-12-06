
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
TARGET_WALLET = os.getenv("TARGET_WALLET")

url = f"https://data-api.polymarket.com/positions?user={TARGET_WALLET}"
response = requests.get(url, timeout=10)
positions = response.json()

print(f"Posições do alvo ({TARGET_WALLET[:10]}...):\n")

for pos in positions[:3]:  # Mostra só 3 para não poluir
    print(json.dumps(pos, indent=2))
    print("-" * 50)
