
import os
from dotenv import load_dotenv
from py_clob_client.client import ClobClient

load_dotenv()
pk = os.getenv("PRIVATE_KEY")
client = ClobClient(host="https://clob.polymarket.com", key=pk, chain_id=137)

asset_id = "22672197750076182435104685732828312699499178229368909069779722995564228197359"

try:
    print(f"Fetching OB for {asset_id}...")
    ob = client.get_order_book(asset_id)
    print("Success:", ob)
except Exception as e:
    print("Failed:", e)
