
import os
from dotenv import load_dotenv
from web3 import Web3
from py_clob_client.client import ClobClient

load_dotenv()
pk = os.getenv("PRIVATE_KEY")
rpc = os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com")

# 1. Derive Address from PK
w3 = Web3(Web3.HTTPProvider(rpc))
account = w3.eth.account.from_key(pk)
my_address = account.address

print(f"🔑 Endereço da Carteira (do .env): {my_address}")

# 2. Check MATIC (POL) Balance
matic_balance = w3.eth.get_balance(my_address)
print(f"⛽ Saldo MATIC/POL: {w3.from_wei(matic_balance, 'ether'):.4f}")

# 3. Check USDC Balance
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174" # Polygon USDC (Native/Bridged)
# Note: There are two USDCs on Polygon.
# USDC.e (Bridged): 0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174 (Most common on Polymarket)
# USDC (Native): 0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359

abi = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"}
]

contract = w3.eth.contract(address=USDC_ADDRESS, abi=abi)
usdc_balance = contract.functions.balanceOf(my_address).call()
print(f"💰 Saldo USDC (Bridged): {usdc_balance / 1_000_000:.2f}")

# Check Native USDC just in case
USDC_NATIVE = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"
contract_native = w3.eth.contract(address=USDC_NATIVE, abi=abi)
usdc_native = contract_native.functions.balanceOf(my_address).call()
print(f"💰 Saldo USDC (Native): {usdc_native / 1_000_000:.2f}")
