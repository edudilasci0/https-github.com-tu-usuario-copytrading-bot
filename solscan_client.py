import requests

SOLSCAN_API_URL = "https://public-api.solscan.io"

def get_wallet_transactions(wallet_address):
    """
    Obtiene las transacciones recientes de una wallet desde Solscan.
    """
    url = f"{SOLSCAN_API_URL}/account/transactions?address={wallet_address}"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Error al obtener transacciones: {response.json()}")
    return response.json()

def get_token_data(token_address):
    """
    Obtiene datos de un token desde Solscan.
    """
    url = f"{SOLSCAN_API_URL}/token/meta?tokenAddress={token_address}"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Error al obtener datos del token: {response.json()}")
    return response.json()
