import requests
import base64
from solana.keypair import Keypair

SOLSCAN_API_URL = "https://public-api.solscan.io"
GMGN_API_HOST = "https://gmgn.ai"

def get_wallet_transactions(wallet_address):
    url = f"{SOLSCAN_API_URL}/account/transactions?address={wallet_address}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error al obtener transacciones: {response.status_code} - {response.text}")
        return None

def get_token_data(token_address):
    url = f"{SOLSCAN_API_URL}/token/meta?tokenAddress={token_address}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error al obtener datos del token: {response.status_code} - {response.text}")
        return None

def get_swap_route(token_in, token_out, amount, wallet_address, slippage=1.0):
    url = f"{GMGN_API_HOST}/defi/router/v1/sol/tx/get_swap_route"
    params = {
        "token_in_address": token_in,
        "token_out_address": token_out,
        "in_amount": amount,
        "from_address": wallet_address,
        "slippage": slippage
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error al obtener ruta de swap: {response.status_code} - {response.text}")
        return None

def load_wallet(private_key_base64):
    decoded_key = base64.b64decode(private_key_base64)
    wallet = Keypair.from_secret_key(decoded_key)
    return wallet

def test_apis():
    wallet_address = "HUpPyLU8KWisCAr3mzWy2FKT6uuxQ2qGgJQxyTpDoes5"
    token_in = "So11111111111111111111111111111111111111112"
    token_out = "7EYnhQoR9YM3N7UoaKRoA44Uy8JeaZV3qyouov87awMs"
    amount = 100000000

    print("=== Prueba: API de Solscan ===")
    transactions = get_wallet_transactions(wallet_address)
    if transactions:
        print(f"Transacciones obtenidas para la wallet {wallet_address}: {transactions[:2]}")

    print("\n=== Prueba: Datos de Token en Solscan ===")
    token_data = get_token_data(token_out)
    if token_data:
        print(f"Datos obtenidos para el token {token_out}: {token_data}")

    print("\n=== Prueba: API de GMGN ===")
    route = get_swap_route(token_in, token_out, amount, wallet_address)
    if route:
        print(f"Ruta de swap obtenida desde GMGN: {route}")

if __name__ == "__main__":
    test_apis()
