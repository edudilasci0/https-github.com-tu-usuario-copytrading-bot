import requests

def get_wallet_transactions(wallet_address):
    url = f"https://public-api.solscan.io/account/transactions?account={wallet_address}"
    headers = {"accept": "application/json"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.status_code, "message": response.text}
