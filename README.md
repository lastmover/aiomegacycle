# ai omegacycle

cool viz of ai omegacycle till now.

## Project Structure
```
aiomegacycle/
├── index.html
├── README.md
├── requirements.txt
├── .env.template
├── data/
│   ├── main.py
│   ├── codex_chain_ids.json
│   ├── tracked_tokens.json
│   └── historical_data.csv
└── assets/
├── styles.css
├── favicon.ico
└── header.png
```
- **`index.html`**: web page embedding the chart.
- **`data/`**: script and config files to fetch daily market caps.
- **`assets/`**: static images/CSS.

## Add a New Token
In `data/tracked_tokens.json`, add your entry, and submit a pull request. Once merged, the new token will be tracked along with the others.

```
{
  "ticker": "XXX",
  "chain": "solana|base|ethereum",
  "address": "your-token-address"
}
```

## Questions
- Project X: [@aiomegacycle](https://x.com/aiomegacycle)
- My X: [@last_mover](https://x.com/last_mover)