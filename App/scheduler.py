import requests

NODEIP = '65.2.177.164:5000'
# NODEIP = 'localhost:5000'

def send_hello():
    print("---------------i am working schedular ----------------")


def nse_squareoff(coin_type):
    url = f"http://{NODEIP}/api/tradeCoin/squareoff"
    params = {'coinType': coin_type}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status() 
        return response.json() 
    except requests.RequestException as e:
        return f"Request failed: {e}"
    
    

def mini_mcx_squareoff(coin_type):
    url = f"http://{NODEIP}/api/tradeCoin/squareoff"
    params = {'coinType': coin_type}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status() 
        return response.json() 
    except requests.RequestException as e:
        return f"Request failed: {e}"
    
    
def delete_expire():
    url = f"http://{NODEIP}/api/tradeCoin/expire"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return f"Request failed: {e}"