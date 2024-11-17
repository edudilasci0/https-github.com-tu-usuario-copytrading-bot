import os
import time
from datetime import datetime
import requests
from solana.keypair import Keypair
from solana.rpc.api import Client
from solana.transaction import Transaction

# Configuraciones iniciales
GMGN_API_HOST = "https://gmgn.ai"
MAX_TRADES_PER_DAY = 10  # Número máximo de transacciones por día
INITIAL_INVESTMENT = 10  # USD por operación
LIQUIDITY_MIN = 80000  # Liquidez mínima en USD
VOLUME_MIN = 300000  # Volumen diario mínimo en USD
STOP_LOSS_THRESHOLD = 0.45  # Pérdida máxima tolerada (45%)
TAKE_PROFIT_LEVELS = [2, 5, 10]  # Niveles de ganancia (2x, 5x, 10x)

# Registro de transacciones diarias
daily_trade_count = 0
last_trade_date = datetime.now().date()


def reset_daily_trades():
    """
    Reinicia el conteo diario de transacciones al comenzar un nuevo día.
    """
    global daily_trade_count, last_trade_date
    current_date = datetime.now().date()
    if current_date != last_trade_date:
        print(f"Reiniciando conteo diario de trades ({current_date})...")
        daily_trade_count = 0
        last_trade_date = current_date


def validate_transaction(transaction, wallet_tag):
    """
    Valida si la transacción cumple con los criterios de liquidez y volumen.
    """
    token_out = transaction["tokenB"]
    token_data = get_token_data(token_out)  # Obtiene datos del token
    liquidity = token_data.get("liquidity", 0)
    volume = token_data.get("volume", 0)

    if liquidity < LIQUIDITY_MIN or volume < VOLUME_MIN:
        print(f"[{wallet_tag}] Token {token_out} rechazado: Liquidez {liquidity}, Volumen {volume}")
        return False
    return True


def get_swap_route(token_in, token_out, amount, wallet_address, slippage=1.0):
    """
    Obtiene la mejor ruta para un swap usando la API de GMGNai.
    """
    url = f"{GMGN_API_HOST}/defi/router/v1/sol/tx/get_swap_route"
    params = {
        "token_in_address": token_in,
        "token_out_address": token_out,
        "in_amount": amount,
        "from_address": wallet_address,
        "slippage": slippage
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"Error al obtener ruta de swap: {response.json()}")
    
    return response.json()


def submit_signed_transaction(signed_tx):
    """
    Envía una transacción firmada a través de GMGNai.
    """
    url = f"{GMGN_API_HOST}/defi/router/v1/sol/tx/submit_signed_transaction"
    payload = {
        "signed_tx": signed_tx
    }

    response = requests.post(url, json=payload)
    if response.status_code != 200:
        raise Exception(f"Error al enviar transacción: {response.json()}")
    
    return response.json()


def sign_transaction(raw_tx, wallet):
    """
    Firma una transacción usando la wallet.
    """
    transaction = Transaction.deserialize(bytes.fromhex(raw_tx))
    transaction.sign(wallet)
    return transaction.serialize().hex()


def execute_trade(wallet, token_in, token_out, amount):
    """
    Ejecuta un swap usando la API de GMGNai.
    """
    print(f"Iniciando swap: {token_in} -> {token_out}, monto: {amount}")
    
    # Obtener la mejor ruta de swap
    route = get_swap_route(token_in, token_out, amount, wallet.public_key())
    print("Ruta de swap obtenida:", route)

    # Firmar la transacción
    signed_tx = sign_transaction(route["data"]["raw_tx"]["swapTransaction"], wallet)
    
    # Enviar la transacción firmada
    result = submit_signed_transaction(signed_tx)
    print("Resultado del swap:", result)
    return result


def load_wallet():
    """
    Carga la wallet desde una variable de entorno.
    """
    private_key = os.environ.get("PRIVATE_KEY")
    if not private_key:
        raise Exception("Clave privada no configurada. Verifica las variables de entorno.")

    # Convertir clave privada base64 a bytes
    decoded_key = base64.b64decode(private_key)
    return Keypair.from_secret_key(decoded_key)


def main():
    global daily_trade_count
    print("Iniciando monitoreo de wallets...")

    # Simulación: Lista de wallets a monitorear
    wallets = [
        {"tag": "Wallet1", "address": "HUpPyLU8KWisCAr3mzWy2FKT6uuxQ2qGgJQxyTpDoes5"},
        {"tag": "Wallet2", "address": "71CPXu3TvH3iUKaY1bNkAAow24k6tjH473SsKprQBABC"}
    ]

    for wallet in wallets:
        print(f"Monitoreando: {wallet['tag']} ({wallet['address']})")
        transactions = get_wallet_transactions(wallet["address"])

        for tx in transactions:
            # Verificar si se alcanzó el límite diario
            reset_daily_trades()
            if daily_trade_count >= MAX_TRADES_PER_DAY:
                print("Límite diario de transacciones alcanzado. Ignorando más operaciones.")
                break

            # Validar la transacción
            if not validate_transaction(tx, wallet["tag"]):
                continue

            # Configurar los parámetros del trade
            token_in = tx["tokenA"]
            token_out = tx["tokenB"]
            amount = int(INITIAL_INVESTMENT * 1e9)  # Convertir USD a lamports

            # Ejecutar la transacción (comentar si no hay wallet configurada aún)
            # execute_trade(wallet, token_in, token_out, amount)

            # Incrementar el conteo diario
            daily_trade_count += 1
            print(f"Transacción copiada. Trades restantes hoy: {MAX_TRADES_PER_DAY - daily_trade_count}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render necesita que un puerto esté configurado
    print(f"Iniciando en el puerto {port}")
    main()
