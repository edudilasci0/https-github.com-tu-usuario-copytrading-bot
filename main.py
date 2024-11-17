import time
from datetime import datetime
from wallets_manager import load_wallets
from solscan_client import get_wallet_transactions, get_token_data
from gmgn_client import get_swap_route, submit_signed_transaction

# Configuraciones iniciales
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


def apply_strategy(current_price, buy_price, highest_price, position_size, wallet_action):
    """
    Aplica la estrategia de Take Profit, Stop Loss dinámico, y seguimiento de la wallet monitoreada.
    """
    global TAKE_PROFIT_LEVELS, STOP_LOSS_THRESHOLD

    # Manejar acciones de la wallet monitoreada
    if wallet_action == "sell_all":
        print(f"Wallet vendió todo. Cerrando posición.")
        return 0  # Cerrar posición
    elif wallet_action == "sell_partial":
        sell_fraction = 0.5
        sell_amount = position_size * sell_fraction
        print(f"Wallet vendió parcialmente. Vendiendo {sell_amount:.2f} tokens.")
        position_size -= sell_amount

    # Take Profit
    gain = current_price / buy_price
    for tp in TAKE_PROFIT_LEVELS:
        if gain >= tp:
            sell_amount = position_size * (tp / sum(TAKE_PROFIT_LEVELS))
            print(f"Take Profit alcanzado: {tp}x. Vendiendo {sell_amount:.2f} tokens.")
            position_size -= sell_amount

    # Stop Loss dinámico
    dynamic_stop_loss = highest_price * (1 - STOP_LOSS_THRESHOLD)
    if current_price < dynamic_stop_loss:
        print(f"Stop Loss activado: Precio actual {current_price} menor a {dynamic_stop_loss}. Vendiendo todo.")
        return 0  # Cerrar posición

    return position_size


def main():
    global daily_trade_count
    wallets = load_wallets()
    print("Iniciando monitoreo de wallets...")

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

            # Configuración de la operación
            buy_price = tx["price"]
            current_price = tx["current_price"]
            highest_price = buy_price  # Inicializar precio más alto
            position_size = INITIAL_INVESTMENT / buy_price  # Tamaño inicial de la posición

            # Aplicar estrategia
            position_size = apply_strategy(current_price, buy_price, highest_price, position_size, tx.get("action"))

            if position_size == 0:
                print(f"Posición cerrada completamente para {wallet['tag']}.")
            else:
                print(f"Tamaño restante de la posición para {wallet['tag']}: {position_size} tokens.")

            # Incrementar el conteo diario
            daily_trade_count += 1
            print(f"Transacción copiada. Trades restantes hoy: {MAX_TRADES_PER_DAY - daily_trade_count}")


if __name__ == "__main__":
    main()
