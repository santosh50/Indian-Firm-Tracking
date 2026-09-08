import os
import requests
from dotenv import load_dotenv

api_key = os.environ.get("API_KEY", "")

# This is data.gov.in's standard example resource_id
TEST_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"

url = f"https://api.data.gov.in/resource/{TEST_RESOURCE_ID}"
params = {
    "api-key": api_key,
    "format": "json",
    "offset": 0,
    "limit": 5,
}

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

print("Running...")
try:
    response = requests.get(url, params=params, headers=headers, timeout=10)
except requests.exceptions.Timeout:
    print("Request timed out after 10 seconds.")
    print("This usually means: a network/firewall issue, the endpoint is")
    print("temporarily down, or something is blocking outbound HTTPS on")
    print("your machine (VPN, campus network, corporate proxy, etc).")
    print(f"\nTry pasting this URL directly into your browser instead:")
    print(response.url if 'response' in dir() else f"{url}?api-key={API_KEY}&format=json&offset=0&limit=5")
    raise SystemExit(1)
except requests.exceptions.ConnectionError as e:
    print(f"Connection error -- could not reach api.data.gov.in at all: {e}")
    print("Check your internet connection, or whether you're on a network")
    print("(university/office wifi) that blocks this domain.")
    raise SystemExit(1)
 
print(f"Status code: {response.status_code}")
print(f"URL called: {response.url}")
 
if response.status_code == 200:
    data = response.json()
    print(f"\nTotal records available: {data.get('total')}")
    print(f"Fields: {[f['name'] for f in data.get('field', [])]}")
    print(f"\nFirst {len(data.get('records', []))} records:")
    for record in data.get("records", []):
        print(record)
else:
    print("\nRequest failed. Response body:")
    print(response.text)
