import json
import os
import time
import csv
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

CODEX_API_URL = "https://graph.codex.io/graphql"
BIRDEYE_API_URL = "https://public-api.birdeye.so/defi/history_price"

def load_tracked_tokens(filename="tracked_tokens.json") -> List[Dict[str, str]]:
    with open(filename, "r") as f:
        return json.load(f)

def load_codex_chain_ids(filename="codex_chain_ids.json") -> Dict[str, int]:
    with open(filename, "r") as f:
        return json.load(f)

def fetch_token_info(address: str, network_id: int) -> Dict[str, Any]:
    codex_api_key = os.getenv("CODEX_API_KEY")
    headers = {"Content-Type": "application/json", "Authorization": f"{codex_api_key}"}
    query = f"""
        query {{
          getTokenInfo(address: "{address}", networkId: {network_id}) {{
            address
            name
            symbol
            totalSupply
            circulatingSupply
            imageLargeUrl
          }}
        }}
    """
    payload = {"query": query}

    try:
        response = requests.post(CODEX_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["data"]["getTokenInfo"]
    except Exception as e:
        raise Exception(f"Error fetching token info for {address}: {e}")

def fetch_birdeye_prices(address: str, chain: str, from_timestamp: int, to_timestamp: int) -> Dict[datetime, float]:
    """
    Fetches historical daily prices for a token from the Birdeye API.
    Returns a dict of date -> price. If no data for a day, that key won't exist.
    """
    birdeye_api_key = os.getenv("BIRDEYE_API_KEY")
    if not birdeye_api_key:
        raise ValueError("BIRDEYE_API_KEY not found in environment variables.")

    headers = {
        "accept": "application/json",
        "x-chain": chain,
        "X-API-KEY": birdeye_api_key,
    }
    prices = {}
    url = (
        f"{BIRDEYE_API_URL}?"
        f"address={address}&address_type=token&type=1D"
        f"&time_from={from_timestamp}&time_to={to_timestamp}"
    )

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if data and data.get("success"):
            items = data["data"]["items"]
            print(f"{address} ({chain}): retrieved {len(items)} price entries.")
            for item in items:
                date = datetime.fromtimestamp(item["unixTime"]).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                prices[date] = item["value"]
        else:
            print(f"{address} ({chain}): no valid data returned.")
            
        time.sleep(1)  # Rate limiting
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Birdeye prices for {address} on {chain}: {e}")
    except (KeyError, TypeError) as e:
        print(f"Error parsing Birdeye response for {address} on {chain}: {e}")

    return prices

def market_cap_in_millions(value: float) -> float:
    """
    Convert absolute cap to millions (3,200,000 -> 3.2).
    """
    if value is None:
        return 0.0
    return round(value / 1_000_000, 1)

def generate_csv_data() -> List[List[Any]]:
    tracked_tokens = load_tracked_tokens()
    codex_chain_ids = load_codex_chain_ids()

    # We'll start from 2024-10-10
    start_date = datetime(2024, 10, 10)

    # We'll fetch up to 'now', so we don't cut off the last day
    end_date = datetime.now()

    # Build the CSV header
    csv_header = [
        "address",
        "chain",
        "name",
        "symbol",
        "totalSupply",
        "circulatingSupply",
        "image",
    ]

    # Generate a list of dates from start_date to end_date inclusive
    date_list = []
    current_date = start_date
    while current_date <= end_date:
        date_list.append(current_date)
        # Format e.g. "Oct 10, 24"
        csv_header.append(current_date.strftime("%b %d, %y"))
        current_date += timedelta(days=1)

    csv_rows = [csv_header]

    for token in tracked_tokens:
        address = token.get("address", "")
        chain = token.get("chain", "")
        ticker = token.get("ticker", "")

        # Get network ID for Codex
        network_id = codex_chain_ids.get(chain)
        if not network_id:
            print(f"Warning: Codex Chain ID not found for chain: {chain}")
            continue

        # Fetch token info from Codex
        try:
            token_info = fetch_token_info(address, network_id)
        except Exception as e:
            print(f"Error processing {ticker} ({address}): {e}")
            continue

        # Safely handle missing fields
        name = token_info.get("name", "")
        symbol = token_info.get("symbol", "")
        total_supply = token_info.get("totalSupply", 0)
        circ_supply = token_info.get("circulatingSupply", 0)
        image_url = token_info.get("imageLargeUrl", "")

        # Fetch Birdeye prices from start_date -> now
        from_ts = int(start_date.timestamp())
        to_ts = int(datetime.now().timestamp())  # Use current time
        birdeye_prices_dict = fetch_birdeye_prices(address, chain, from_ts, to_ts)

        # Calculate market caps per day
        market_caps = []
        for d in date_list:
            price = birdeye_prices_dict.get(d)
            if price:
                mc = float(price) * float(circ_supply)
                mc_millions = market_cap_in_millions(mc)
                market_caps.append(mc_millions)
            else:
                # No data => zero
                market_caps.append(0)

        # Build row
        csv_row = [
            address,
            chain,
            name,
            symbol,
            total_supply,
            circ_supply,
            image_url,
            *market_caps,
        ]
        csv_rows.append(csv_row)

    return csv_rows

def save_csv(data: List[List[Any]], filename="historical_data.csv"):
    """Save CSV rows using Python's csv module."""
    with open(filename, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(data)

    print(f"CSV data saved to {filename}")

def main():
    csv_data = generate_csv_data()
    save_csv(csv_data)

if __name__ == "__main__":
    main()