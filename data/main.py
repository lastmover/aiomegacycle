import json
import os
import csv
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

CODEX_API_URL = "https://graph.codex.io/graphql"
BIRDEYE_API_URL = "https://public-api.birdeye.so/defi/history_price"


def load_tracked_tokens(filename="tracked_tokens.json") -> List[Dict[str, Any]]:
    """Loads tracked tokens from JSON."""
    with open(filename, "r") as f:
        return json.load(f)


def load_codex_chain_ids(filename="codex_chain_ids.json") -> Dict[str, int]:
    """Loads Codex chain IDs from JSON."""
    with open(filename, "r") as f:
        return json.load(f)


def get_codex_token_info(address: str, network_id: int) -> Dict[str, Any]:
    """Fetches name, symbol, and image from Codex."""
    try:
        api_key = os.getenv("CODEX_API_KEY")
        headers = {"Content-Type": "application/json", "Authorization": f"{api_key}"}
        query = f"""
            query {{
              getTokenInfo(address: "{address}", networkId: {network_id}) {{
                name
                symbol
                imageLargeUrl
              }}
            }}
        """
        r = requests.post(CODEX_API_URL, headers=headers, json={"query": query})
        r.raise_for_status()
        return r.json()["data"]["getTokenInfo"]
    except Exception:
        return {}


def get_birdeye_prices(
    address: str, chain: str, start_ts: int, end_ts: int
) -> Dict[datetime, float]:
    """
    Fetches daily token prices from Birdeye.
    Returns a dict of date -> price. Missing days are omitted.
    """
    prices = {}
    api_key = os.getenv("BIRDEYE_API_KEY")
    if not api_key:
        raise ValueError("BIRDEYE_API_KEY not found.")
    headers = {"accept": "application/json", "x-chain": chain, "X-API-KEY": api_key}
    url = (
        f"{BIRDEYE_API_URL}?address={address}&address_type=token&type=1D"
        f"&time_from={start_ts}&time_to={end_ts}"
    )
    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if data.get("success"):
            items = data["data"]["items"]
            print(f"{address} ({chain}): retrieved {len(items)} price entries.")
            for item in items:
                day = datetime.fromtimestamp(item["unixTime"]).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                prices[day] = item["value"]
        time.sleep(1)
    except Exception as e:
        print(f"Birdeye error for {address} ({chain}): {e}")
    return prices


def generate_csv_data() -> List[List[Any]]:
    """Generates the CSV data with daily market caps."""
    tokens = load_tracked_tokens()
    chain_ids = load_codex_chain_ids()
    start = datetime(2024, 10, 10)
    end = datetime.now()
    csv_header = ["address", "chain", "name", "symbol", "image"]
    date_list = []
    d = start
    while d <= end:
        date_list.append(d)
        csv_header.append(d.strftime("%b %d, %y"))
        d += timedelta(days=1)

    rows = [csv_header]
    for t in tokens:
        address, chain = t.get("address", ""), t.get("chain", "")
        total_supply = t.get("totalSupply", 0)
        net_id = chain_ids.get(chain, 0)
        token_info = get_codex_token_info(address, net_id) if net_id else {}
        name = token_info.get("name", "")
        symbol = token_info.get("symbol", "")
        image = token_info.get("imageLargeUrl", "")
        prices = get_birdeye_prices(
            address, chain, int(start.timestamp()), int(end.timestamp())
        )
        daily_caps = []
        for day in date_list:
            price = prices.get(day, 0)
            mc = price * total_supply
            daily_caps.append(round(mc / 1_000_000, 1) if price else 0)
        rows.append([address, chain, name, symbol, image, *daily_caps])

    return rows


def save_csv(data: List[List[Any]], filename="historical_data.csv"):
    """Writes CSV data to file."""
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(data)
    print(f"CSV saved to {filename}")


def main():
    """Main entry point."""
    csv_data = generate_csv_data()
    save_csv(csv_data)


if __name__ == "__main__":
    main()
