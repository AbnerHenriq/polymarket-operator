
import os
from dotenv import load_dotenv
from py_clob_client.client import ClobClient

load_dotenv()
pk = os.getenv("PRIVATE_KEY")

print("🔑 Inicializando cliente...")
client = ClobClient(host="https://clob.polymarket.com", key=pk, chain_id=137)

try:
    print("🛠️ Tentando criar/derivar credenciais...")
    creds = client.create_or_derive_api_creds()
    print("✅ Credenciais obtidas:")
    print(f"API Key: {creds.api_key}")
    print(f"API Secret: {creds.api_secret[0:5]}...")
    print(f"Passphrase: {creds.api_passphrase[0:5]}...")
    
    # Teste de uso
    client.set_api_creds(creds)
    print("✅ Credenciais aplicadas no cliente.")
    
    # Tenta um endpoint autenticado simples
    print("🧪 Testando endpoint autenticado (get_api_keys)...")
    keys = client.get_api_keys()
    print("✅ Sucesso! Chaves encontradas:", keys)
    
except Exception as e:
    print(f"❌ Erro: {e}")
