import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Configuration & Secrets ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TARGET_WALLET = os.getenv("TARGET_WALLET")

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
