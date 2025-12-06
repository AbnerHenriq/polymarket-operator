import os
import json
import requests
import time
from datetime import datetime
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs
from py_clob_client.constants import POLYGON
from py_clob_client.exceptions import PolyApiException

from web3 import Web3

# Load environment variables
load_dotenv()

# --- Configuration & Secrets ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TARGET_WALLET = os.getenv("TARGET_WALLET")

# Trading Config
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
POLYGON_RPC_URL = os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com")
MAX_TRADE_AMOUNT = float(os.getenv("MAX_TRADE_AMOUNT", "10"))
FIXED_TRADE_AMOUNT = float(os.getenv("FIXED_TRADE_AMOUNT", "1"))
DRY_RUN = os.getenv("DRY_RUN", "True").lower() == "true"

# USDC Config (Polygon)
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
USDC_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    }
]

def init_clob_client():
    """Inicializa o cliente CLOB para trading"""
    if not PRIVATE_KEY:
        print("⚠️ PRIVATE_KEY não configurada. Modo apenas monitoramento.")
        return None
    
    try:
        # Deriva endereço da chave privada para garantir
        w3 = Web3()
        account = w3.eth.account.from_key(PRIVATE_KEY)
        my_address = account.address
        print(f"🔑 Inicializando para carteira: {my_address}")

        client = ClobClient(
            host="https://clob.polymarket.com",
            key=PRIVATE_KEY,
            chain_id=137, # Polygon Mainnet
            signature_type=0, # EOA (MetaMask, chave privada direta)
            funder=my_address # Explicitamente define o funder
        )
        # Tenta derivar credenciais (necessário para alguns endpoints)
        try:
            creds = client.create_or_derive_api_creds()
            client.set_api_creds(creds)
            print("🔑 Credenciais de API derivadas e configuradas.")
            
            # Verifica se está funcionando
            client.get_api_keys()
            print("✅ Autenticação verificada com sucesso.")
            
        except Exception as e:
            print(f"❌ ERRO CRÍTICO: Falha ao configurar credenciais de API: {e}")
            return None
            
        return client
    except Exception as e:
        print(f"Erro ao inicializar ClobClient: {e}")
        return None

def get_usdc_balance(client):
    """Verifica saldo de USDC na carteira"""
    try:
        w3 = Web3(Web3.HTTPProvider(POLYGON_RPC_URL))
        if not w3.is_connected():
            print("⚠️ Não foi possível conectar ao RPC Polygon.")
            return 0
            
        my_address = client.get_address()
        contract = w3.eth.contract(address=USDC_ADDRESS, abi=USDC_ABI)
        
        # Balance vem em Wei (6 decimais para USDC)
        balance_wei = contract.functions.balanceOf(my_address).call()
        balance_usdc = balance_wei / 1_000_000 # USDC tem 6 casas decimais
        
        return balance_usdc
    except Exception as e:
        print(f"Erro ao verificar saldo: {e}")
        return 0

def execute_trade(client, asset_id, side, title, outcome=None):
    """Executa uma ordem de compra/venda"""
    if not client:
        return
        
    try:
        # 1. Busca Orderbook para pegar preço atual
        # O lado oposto: Se quero COMPRAR (BUY), olho o preço de VENDA (ASK)
        book_side = "sell" if side == "BUY" else "buy"
        orderbook = client.get_order_book(asset_id)
        
        price = 0
        if book_side == "sell" and orderbook.asks:
            price = float(orderbook.asks[0].price) # Melhor preço de venda
        elif book_side == "buy" and orderbook.bids:
            price = float(orderbook.bids[0].price) # Melhor preço de compra
            
        if price <= 0:
            print(f"❌ Preço inválido para {title}: {price}")
            return

        # 1.5 Verifica Saldo
        balance = get_usdc_balance(client)
        print(f"💰 Saldo Atual: ${balance:.2f} USDC")
        
        if balance < FIXED_TRADE_AMOUNT:
            print(f"⚠️ Saldo insuficiente! Necessário: ${FIXED_TRADE_AMOUNT}, Disponível: ${balance:.2f}")
            send_telegram_message(f"⚠️ *FALHA NO COPY TRADE*\nSaldo insuficiente.\nNecessário: ${FIXED_TRADE_AMOUNT}\nDisponível: ${balance:.2f}")
            return

        # 2. Calcula tamanho da ordem (Shares)
        # Size = Valor Fixo / Preço
        # Arredondamos para CIMA para garantir que o total seja >= $1.00 (mínimo da Polymarket)
        import math
        size = FIXED_TRADE_AMOUNT / price
        size = math.ceil(size * 100) / 100  # Arredonda para cima com 2 casas decimais
        
        if size <= 0:
            print("❌ Tamanho da ordem calculado é 0.")
            return

        outcome_str = f" ({outcome})" if outcome else ""
        print(f"🤖 Preparando Trade: {side} {size} shares de '{title}'{outcome_str} @ {price} (Total: ${size*price:.2f})")
        
        if DRY_RUN:
            print("🚧 DRY RUN: Ordem não enviada.")
            return

        # 3. Envia Ordem (FOK - Fill Or Kill para garantir execução imediata ou nada)
        # Precisamos do Token ID? O asset_id do Data API geralmente é o Token ID.
        # Data API 'asset' field = Token ID (geralmente um hash longo)
        
        order_args = OrderArgs(
            price=price,
            size=size,
            side=side.upper(),
            token_id=asset_id
        )
        
        # Assina e envia
        # Nota: A versão atual da lib usa GTC por padrão e FOK não parece estar exposto diretamente no OrderArgs simples.
        # Para FOK, precisaríamos usar opções avançadas ou outra chamada.
        # Por enquanto, vamos de GTC (Good Till Cancelled) que é o padrão.
        resp = client.create_and_post_order(order_args)
        print(f"✅ Ordem Enviada! ID: {resp.get('orderID')}")
        send_telegram_message(f"🤖 *COPY TRADE EXECUTADO*\n{side} {size} de {title}\nOutcome: {outcome or 'N/A'}\nPreço: {price}")
        
    except PolyApiException as e:
        if e.status_code == 404:
            print(f"⚠️ Orderbook não encontrado para {title} (Mercado fechado/resolvido?)")
        else:
            print(f"❌ Erro API Polymarket: {e}")
            send_telegram_message(f"❌ *ERRO API POLYMARKET*\n{str(e)}")
            
    except Exception as e:
        print(f"❌ Erro ao executar trade: {e}")
        send_telegram_message(f"❌ *ERRO NO COPY TRADE*\n{str(e)}")

# Arquivo para salvar estado das posições
POSITIONS_FILE = 'last_positions.json'

def get_positions():
    """Busca posições atuais do usuário via Data API"""
    try:
        url = "https://data-api.polymarket.com/positions"
        
        params = {
            'user': TARGET_WALLET
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Retorna lista de posições
        return data if isinstance(data, list) else []
        
    except Exception as e:
        print(f"Erro ao buscar posições: {e}")
        return []

def load_last_positions():
    """Carrega últimas posições conhecidas (asset -> size)"""
    try:
        if os.path.exists(POSITIONS_FILE):
            with open(POSITIONS_FILE, 'r') as f:
                return json.load(f)
        return {}
    except:
        return {}

def save_last_positions(positions_map):
    """Salva estado atual das posições"""
    try:
        with open(POSITIONS_FILE, 'w') as f:
            json.dump(positions_map, f)
    except Exception as e:
        print(f"Erro ao salvar posições: {e}")

def format_position_update(position, change_type, diff_size=0):
    """Formata alerta de mudança de posição"""
    try:
        title = position.get('title', 'Unknown Market')
        outcome = position.get('outcome', 'Unknown')
        current_size = float(position.get('size', 0))
        avg_price = float(position.get('avgPrice', 0))
        current_value = float(position.get('currentValue', 0))
        pnl = float(position.get('percentPnl', 0)) * 100
        
        # Emojis e Textos
        if change_type == 'NEW':
            header = "🆕 *Nova Posição Detectada*"
            emoji = "✨"
            action_text = f"Comprou {current_size:.1f} shares"
        elif change_type == 'INCREASE':
            header = "📈 *Aumento de Posição*"
            emoji = "➕"
            action_text = f"Adicionou {diff_size:.1f} shares"
        elif change_type == 'DECREASE':
            header = "📉 *Redução de Posição*"
            emoji = "➖"
            action_text = f"Vendeu {abs(diff_size):.1f} shares"
        else:
            return None

        # Formata preço
        price_cents = int(avg_price * 100)
        
        message = f"""
{emoji} {header}

👤 *Wallet:* {TARGET_WALLET[:6]}...
🎯 *Market:* {title}
💰 *Outcome:* {outcome} ({price_cents}¢)
📝 *Action:* {action_text}
� *Total Size:* {current_size:.1f}
💵 *Current Value:* ${current_value:.2f}
📈 *P/L:* {pnl:+.1f}%

[Ver no Polymarket](https://polymarket.com/profile/{TARGET_WALLET})
"""
        return message
    except Exception as e:
        print(f"Erro ao formatar mensagem: {e}")
        return None

def send_telegram_message(message):
    """Envia mensagem via Telegram"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials not set.")
        return False
        
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }
        
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        print("Mensagem enviada com sucesso!")
        return True
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")
        return False

def main():
    print(f"Iniciando monitoramento de posições - {datetime.now()}")
    
    if not TARGET_WALLET:
        print("TARGET_WALLET not set in .env")
        return

    # Inicializa cliente de trading
    clob_client = init_clob_client()

    # 1. Busca posições atuais na API
    current_positions_list = get_positions()
    print(f"Encontradas {len(current_positions_list)} posições ativas")
    
    # Cria mapa {asset_id: dados_posicao}
    current_positions_map = {}
    for pos in current_positions_list:
        asset = pos.get('asset')
        if asset:
            current_positions_map[asset] = pos

    # 2. Carrega estado anterior
    last_positions_map = load_last_positions()
    
    # Se não tiver estado anterior, assume vazio para alertar sobre as posições atuais
    if not last_positions_map:
        print("Primeira execução: Alertando sobre posições atuais...")


    # 3. Compara estados para detectar mudanças
    changes_detected = False
    
    # Verifica Novas e Aumentos
    for asset, pos in current_positions_map.items():
        current_size = float(pos.get('size', 0))
        
        if asset not in last_positions_map:
            # Nova Posição
            print(f"Nova posição encontrada: {pos.get('title')}")
            msg = format_position_update(pos, 'NEW')
            if msg: send_telegram_message(msg)
            
            # COPY TRADE
            if clob_client:
                execute_trade(clob_client, asset, "BUY", pos.get('title'), pos.get('outcome'))
                
            changes_detected = True
            
        else:
            # Posição Existente - Verifica mudança de tamanho
            last_size = float(last_positions_map.get(asset, 0))
            diff = current_size - last_size
            
            # Considera mudança apenas se for significativa (> 0.1 shares para evitar ruído de arredondamento)
            if diff > 0.1:
                print(f"Aumento de posição: {pos.get('title')}")
                msg = format_position_update(pos, 'INCREASE', diff)
                if msg: send_telegram_message(msg)
                
                # COPY TRADE
                if clob_client:
                    execute_trade(clob_client, asset, "BUY", pos.get('title'), pos.get('outcome'))
                    
                changes_detected = True
            elif diff < -0.1:
                print(f"Redução de posição: {pos.get('title')}")
                msg = format_position_update(pos, 'DECREASE', diff)
                if msg: send_telegram_message(msg)
                changes_detected = True

    # Verifica Posições Fechadas (Zeradas)
    # Se estava no last_map mas não está no current_map (ou size=0), foi vendida tudo
    for asset, last_size in last_positions_map.items():
        if asset not in current_positions_map:
            # Posição foi encerrada
            # Precisamos dos dados antigos para notificar, mas não temos o objeto 'pos' completo aqui facilmente
            # a menos que tenhamos salvo tudo. Por simplificação, vamos ignorar ou tentar reconstruir.
            # Se quisermos alertar venda total, precisaríamos ter salvo os metadados antes.
            # Por enquanto, vamos focar em Novas/Mudanças de posições ativas.
            pass

    if not changes_detected:
        print("Nenhuma mudança nas posições.")

    # 4. Salva novo estado
    # Salva {asset: size} para a próxima comparação
    new_state = {k: float(v.get('size', 0)) for k, v in current_positions_map.items()}
    save_last_positions(new_state)
    print("Monitoramento concluído")

if __name__ == "__main__":
    main()
