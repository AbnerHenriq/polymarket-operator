"""
Script para verificar suas posições na EOA (carteira direta) no Polymarket
"""

import os
import requests
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

PRIVATE_KEY = os.getenv("PRIVATE_KEY")

# Deriva endereço da chave privada
w3 = Web3()
account = w3.eth.account.from_key(PRIVATE_KEY)
MY_ADDRESS = account.address

print(f"🔍 Verificando posições para: {MY_ADDRESS}")
print("=" * 60)

# Consulta a API de posições do Polymarket
url = f"https://data-api.polymarket.com/positions?user={MY_ADDRESS}"

try:
    response = requests.get(url, timeout=10)
    positions = response.json()
    
    if not positions:
        print("❌ Nenhuma posição encontrada nesta carteira.")
        print("\n💡 Isso pode significar que:")
        print("   1. As ordens foram enviadas mas não preenchidas (pending)")
        print("   2. As posições estão em outra carteira (Proxy Wallet)")
        print("   3. Houve algum erro na execução")
    else:
        print(f"✅ Encontradas {len(positions)} posições:\n")
        
        total_value = 0
        for pos in positions:
            title = pos.get('title', 'Sem título')
            outcome = pos.get('outcome', '?')
            size = float(pos.get('size', 0))
            avg_price = float(pos.get('avgPrice', 0))
            current_value = float(pos.get('currentValue', 0))
            pnl = float(pos.get('pnl', 0))
            
            print(f"📊 {title}")
            print(f"   Outcome: {outcome}")
            print(f"   Shares: {size:.2f}")
            print(f"   Preço Médio: ${avg_price:.4f}")
            print(f"   Valor Atual: ${current_value:.2f}")
            print(f"   PnL: ${pnl:.2f}")
            print()
            
            total_value += current_value
        
        print("=" * 60)
        print(f"💰 Valor Total das Posições: ${total_value:.2f}")

except Exception as e:
    print(f"❌ Erro ao consultar posições: {e}")

# Também verifica ordens pendentes
print("\n" + "=" * 60)
print("📋 Verificando ordens pendentes/recentes...")

from py_clob_client.client import ClobClient

try:
    client = ClobClient(
        host="https://clob.polymarket.com",
        key=PRIVATE_KEY,
        chain_id=137,
        signature_type=0,
        funder=MY_ADDRESS
    )
    creds = client.create_or_derive_api_creds()
    client.set_api_creds(creds)
    
    # Busca ordens
    orders = client.get_orders()
    
    if orders:
        print(f"✅ Encontradas {len(orders)} ordens:\n")
        for order in orders[:10]:  # Limita a 10
            print(f"   ID: {order.get('id', '?')[:20]}...")
            print(f"   Status: {order.get('status', '?')}")
            print(f"   Side: {order.get('side', '?')}")
            print(f"   Size: {order.get('original_size', '?')}")
            print(f"   Price: {order.get('price', '?')}")
            print()
    else:
        print("   Nenhuma ordem pendente encontrada.")
        
except Exception as e:
    print(f"❌ Erro ao buscar ordens: {e}")
