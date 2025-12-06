"""
Script para configurar as allowances (permissões) necessárias para trading na Polymarket.
Você só precisa rodar isso UMA VEZ por carteira.
"""

import os
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

PRIVATE_KEY = os.getenv("PRIVATE_KEY")
POLYGON_RPC_URL = os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com")

# Conecta à rede
w3 = Web3(Web3.HTTPProvider(POLYGON_RPC_URL))
account = w3.eth.account.from_key(PRIVATE_KEY)
my_address = account.address

print(f"🔑 Endereço: {my_address}")
print(f"⛽ Saldo POL: {w3.from_wei(w3.eth.get_balance(my_address), 'ether'):.4f}")

# Contratos a aprovar
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
CTF_ADDRESS = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"  # Conditional Token Framework

SPENDERS = [
    ("Main Exchange", "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"),
    ("Neg Risk Exchange", "0xC5d563A36AE78145C45a50134d48A1215220f80a"),
    ("Neg Risk Adapter", "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"),
]

# ABI mínima para ERC-20 approve
ERC20_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    }
]

# ABI mínima para ERC-1155 setApprovalForAll (Conditional Tokens)
ERC1155_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "operator", "type": "address"},
            {"name": "approved", "type": "bool"}
        ],
        "name": "setApprovalForAll",
        "outputs": [],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [
            {"name": "account", "type": "address"},
            {"name": "operator", "type": "address"}
        ],
        "name": "isApprovedForAll",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
]

MAX_UINT256 = 2**256 - 1

def approve_erc20(token_address, token_name, spender_name, spender_address):
    """Aprova um spender para gastar um token ERC-20"""
    contract = w3.eth.contract(address=token_address, abi=ERC20_ABI)
    
    # Verifica allowance atual
    current_allowance = contract.functions.allowance(my_address, spender_address).call()
    
    if current_allowance > 0:
        print(f"  ✅ {token_name} já aprovado para {spender_name}")
        return True
    
    print(f"  🔄 Aprovando {token_name} para {spender_name}...")
    
    try:
        tx = contract.functions.approve(spender_address, MAX_UINT256).build_transaction({
            'from': my_address,
            'nonce': w3.eth.get_transaction_count(my_address),
            'gas': 100000,
            'gasPrice': w3.eth.gas_price,
            'chainId': 137
        })
        
        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        print(f"    📤 TX enviada: {tx_hash.hex()}")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        if receipt.status == 1:
            print(f"    ✅ Aprovado com sucesso!")
            return True
        else:
            print(f"    ❌ Transação falhou!")
            return False
            
    except Exception as e:
        print(f"    ❌ Erro: {e}")
        return False

def approve_erc1155(token_address, token_name, spender_name, spender_address):
    """Aprova um spender para gastar tokens ERC-1155"""
    contract = w3.eth.contract(address=token_address, abi=ERC1155_ABI)
    
    # Verifica se já está aprovado
    is_approved = contract.functions.isApprovedForAll(my_address, spender_address).call()
    
    if is_approved:
        print(f"  ✅ {token_name} já aprovado para {spender_name}")
        return True
    
    print(f"  🔄 Aprovando {token_name} para {spender_name}...")
    
    try:
        tx = contract.functions.setApprovalForAll(spender_address, True).build_transaction({
            'from': my_address,
            'nonce': w3.eth.get_transaction_count(my_address),
            'gas': 100000,
            'gasPrice': w3.eth.gas_price,
            'chainId': 137
        })
        
        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        print(f"    📤 TX enviada: {tx_hash.hex()}")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        if receipt.status == 1:
            print(f"    ✅ Aprovado com sucesso!")
            return True
        else:
            print(f"    ❌ Transação falhou!")
            return False
            
    except Exception as e:
        print(f"    ❌ Erro: {e}")
        return False

def main():
    print("\n📜 Configurando Allowances para Polymarket...")
    print("=" * 50)
    
    # Aprova USDC (ERC-20) para todos os spenders
    print("\n💵 USDC:")
    for spender_name, spender_address in SPENDERS:
        approve_erc20(USDC_ADDRESS, "USDC", spender_name, spender_address)
    
    # Aprova CTF (ERC-1155) para todos os spenders
    print("\n🎲 Conditional Tokens:")
    for spender_name, spender_address in SPENDERS:
        approve_erc1155(CTF_ADDRESS, "CTF", spender_name, spender_address)
    
    print("\n" + "=" * 50)
    print("✅ Configuração concluída!")
    print("Agora você pode rodar o bot: python src/bot.py")

if __name__ == "__main__":
    main()
