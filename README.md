# 🔗 Wallet Risk Analyzer — GitHub Action

Generate on-chain risk audit reports for any Ethereum address. Uses only public RPC endpoints — **no API keys required**.

## Features

- 📊 Balance, transaction count, and token holdings
- ⚠️ Risk detection: failed txs, high gas, dormant wallets, contract addresses
- 🪙 ERC-20 token interaction history
- 📄 Beautiful HTML report + JSON data
- 🔒 Zero sensitive data access — public blockchain only

## Quick Start

```yaml
- name: Wallet Risk Audit
  uses: richard202605/wallet-risk-action@v1
  with:
    address: '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045'
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `address` | ✅ | — | Ethereum address to audit (0x... format) |
| `output-format` | ❌ | `both` | Output format: `html`, `json`, or `both` |

## Outputs

| Output | Description |
|--------|-------------|
| `balance-eth` | Wallet balance in ETH |
| `balance-usd` | Wallet balance in USD |
| `risk-count` | Number of risks detected |
| `report-path` | Path to generated HTML report |

## Example: Audit in CI + PR Comment

```yaml
name: Wallet Audit
on:
  workflow_dispatch:
    inputs:
      address:
        description: 'Ethereum address'
        required: true

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Wallet Risk Audit
        id: audit
        uses: richard202605/wallet-risk-action@v1
        with:
          address: ${{ inputs.address }}

      - name: Comment on PR
        if: github.event_name == 'pull_request'
        uses: marocchino/sticky-pull-request-comment@v2
        with:
          message: |
            ## 🔗 Wallet Risk Audit
            - **Balance:** ${{ steps.audit.outputs.balance-eth }} ETH
            - **Risks:** ${{ steps.audit.outputs.risk-count }}
            - [View Full Report](${{ steps.audit.outputs.report-path }})
```

## Example: Batch Audit Multiple Addresses

```yaml
- name: Audit Treasury
  uses: richard202605/wallet-risk-action@v1
  with:
    address: '0x...treasury...'

- name: Audit Multisig
  uses: richard202605/wallet-risk-action@v1
  with:
    address: '0x...multisig...'
```

## What It Checks

| Check | Level | Description |
|-------|-------|-------------|
| Zero Balance | INFO | New or inactive address |
| Contract Address | Warning | May have custom logic |
| Failed Transactions | INFO | Potential contract issues |
| High Gas Usage | Warning | Complex interactions (>500k gas) |
| Dormant Wallet | INFO | No activity for 365+ days |

## How It Works

1. Queries public Ethereum RPC endpoints for balance, tx count, and code
2. Fetches recent transactions from Etherscan v2 API (no key needed for basic queries)
3. Analyzes ERC-20 token transfers
4. Generates risk assessment + HTML report
5. Uploads report as GitHub Actions artifact

## CLI Usage

```bash
# Clone and run locally
git clone https://github.com/richard202605/wallet-risk-action.git
cd wallet-risk-action
python3 scripts/wallet_risk_analyzer.py 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# With custom output directory
python3 scripts/wallet_risk_analyzer.py 0x... --output-dir ./my-reports
```

## Need More?

This Action is built by **FlowForge AI Ops** — we provide:

| Service | Price | Delivery |
|---------|-------|----------|
| Wallet Security Audit | $200-400 | 48-72 hours |
| Smart Contract Documentation | $400-800 | 72-96 hours |
| Web3 Developer Tutorial | $200-400 | 48-72 hours |

📧 [Contact us](https://richard202605.github.io/web3-docs-service/) | 📂 [Portfolio](https://richard202605.github.io/midnight-tutorials-portfolio/)

## License

MIT
