import os
import requests
from datetime import datetime
from solana.keypair import Keypair
from solana.rpc.api import Client
from solana.transaction import Transaction

# Configuraciones iniciales
CIELO_API_URL = "https://feed-api.cielo.finance/api/v1/feed"
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


def get_wallet_transactions(wallet_address, limit=10):
    """
    Consulta el feed de Cielo Finance para obtener las transacciones recientes de una wallet.
    """
    params = {
        "address": wallet_address,
        "limit": limit,
        "chain": "Solana",
    }
    headers = {
        "Authorization": f"Bearer {os.getenv('CIELO_API_KEY')}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(CIELO_API_URL, params=params, headers=headers)
        response.raise_for_status()
        return response.json().get("transactions", [])
    except requests.exceptions.RequestException as e:
        print(f"[Error] No se pudo obtener transacciones de {wallet_address}: {e}")
        return []


def validate_transaction(transaction, wallet_tag):
    """
    Valida si la transacción cumple con los criterios de liquidez y volumen.
    """
    token_out = transaction["tokenB"]
    liquidity = transaction.get("liquidityUSD", 0)
    volume = transaction.get("volumeUSD", 0)

    if liquidity < LIQUIDITY_MIN or volume < VOLUME_MIN:
        print(f"[{wallet_tag}] Token {token_out} rechazado: Liquidez {liquidity}, Volumen {volume}")
        return False
    return True


def get_swap_route(token_in, token_out, amount, wallet_address, slippage=1.0):
    """
    Obtiene la mejor ruta para un swap usando la API de GMGN.
    """
    url = f"{GMGN_API_HOST}/defi/router/v1/sol/tx/get_swap_route"
    params = {
        "token_in_address": token_in,
        "token_out_address": token_out,
        "in_amount": amount,
        "from_address": wallet_address,
        "slippage": slippage,
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"Error al obtener ruta de swap: {response.json()}")

    return response.json()


def submit_signed_transaction(signed_tx):
    """
    Envía una transacción firmada a través de GMGN.
    """
    url = f"{GMGN_API_HOST}/defi/router/v1/sol/tx/submit_signed_transaction"
    payload = {"signed_tx": signed_tx}

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
    Ejecuta un swap usando la API de GMGN.
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


def main():
    global daily_trade_count
    print("Iniciando monitoreo de wallets...")

    # Lista de wallets a monitorear
    wallets = [
        {"tag": "Wallet1", "address": "HUpPyLU8KWisCAr3mzWy2FKT6uuxQ2qGgJQxyTpDoes5"},
        {"tag": "Wallet2", "address": "71CPXu3TvH3iUKaY1bNkAAow24k6tjH473SsKprQBABC"},
    ]

    for wallet in wallets:
        print(f"Monitoreando: {wallet['tag']} ({wallet['address']})")
        transactions = get_wallet_transactions(wallet["address"], limit=10)

        for tx in transactions:
            # Reinicia el conteo diario si es necesario
            reset_daily_trades()

            if daily_trade_count >= MAX_TRADES_PER_DAY:
                print("Límite diario de transacciones alcanzado. Ignorando más operaciones.")
                break

            # Valida la transacción antes de copiar
            if not validate_transaction(tx, wallet["tag"]):
                continue

            # Configurar los parámetros del trade
            token_in = tx["tokenA"]
            token_out = tx["tokenB"]
            amount = int(INITIAL_INVESTMENT * 1e9)  # Convertir USD a lamports

            # Ejecutar la transacción
            execute_trade(wallet, token_in, token_out, amount)

            # Incrementar el conteo diario
            daily_trade_count += 1
            print(f"Transacción copiada. Trades restantes hoy: {MAX_TRADES_PER_DAY - daily_trade_count}")


if __name__ == "__main__":
    main()
