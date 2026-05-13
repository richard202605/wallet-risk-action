#!/usr/bin/env python3
"""
Wallet On-Chain Risk Analyzer v1.0
Generates HTML risk audit reports from public blockchain data.
Usage: python3 wallet_risk_analyzer.py <ethereum_address> [--output-dir DIR]
Output: Terminal report + HTML report + JSON data

No private keys, seed phrases, or sensitive data required.
Uses only public RPC endpoints and Etherscan v2 API.
"""

import json
import sys
import urllib.request
import urllib.parse
import datetime
import os
from typing import Optional

# ─── Config ────────────────────────────────────────────────
RPC_ENDPOINTS = [
    "https://ethereum-rpc.publicnode.com",
    "https://rpc.flashbots.net",
    "https://cloudflare-eth.com",
]
ETHERSCAN_API = "https://api.etherscan.io/v2/api"
COINGECKO_PRICE = "https://api.coingecko.com/api/v3/simple/price"
DEFAULT_REPORT_DIR = os.path.join(os.getcwd(), "wallet-audit")


def rpc_call(method: str, params: list, endpoint_idx: int = 0) -> Optional[dict]:
    for i in range(len(RPC_ENDPOINTS)):
        idx = (endpoint_idx + i) % len(RPC_ENDPOINTS)
        url = RPC_ENDPOINTS[idx]
        payload = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json", "User-Agent": "WalletRiskAnalyzer/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            if "result" in data:
                return data
        except Exception:
            continue
    return None


def get_balance(address: str) -> float:
    result = rpc_call("eth_getBalance", [address, "latest"])
    return int(result["result"], 16) / 10**18 if result and "result" in result else 0.0


def get_tx_count(address: str) -> int:
    result = rpc_call("eth_getTransactionCount", [address, "latest"])
    return int(result["result"], 16) if result and "result" in result else 0


def get_code(address: str) -> str:
    result = rpc_call("eth_getCode", [address, "latest"])
    return result["result"] if result and "result" in result else "0x"


def get_eth_price() -> dict:
    url = f"{COINGECKO_PRICE}?ids=ethereum&vs_currencies=usd,cny"
    req = urllib.request.Request(url, headers={"User-Agent": "WalletRiskAnalyzer/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()).get("ethereum", {"usd": 0, "cny": 0})
    except Exception:
        return {"usd": 0, "cny": 0}


def get_recent_txs_etherscan(address: str, limit: int = 20) -> list:
    url = f"{ETHERSCAN_API}?chainid=1&module=account&action=txlist&address={address}&startblock=0&endblock=99999999&page=1&offset={limit}&sort=desc"
    req = urllib.request.Request(url, headers={"User-Agent": "WalletRiskAnalyzer/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        return data["result"] if data.get("status") == "1" and data.get("result") else []
    except Exception:
        return []


def get_erc20_transfers_etherscan(address: str, limit: int = 20) -> list:
    url = f"{ETHERSCAN_API}?chainid=1&module=account&action=tokentx&address={address}&startblock=0&endblock=99999999&page=1&offset={limit}&sort=desc"
    req = urllib.request.Request(url, headers={"User-Agent": "WalletRiskAnalyzer/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        return data["result"] if data.get("status") == "1" and data.get("result") else []
    except Exception:
        return []


def get_internal_txs_etherscan(address: str, limit: int = 10) -> list:
    url = f"{ETHERSCAN_API}?chainid=1&module=account&action=txlistinternal&address={address}&startblock=0&endblock=99999999&page=1&offset={limit}&sort=desc"
    req = urllib.request.Request(url, headers={"User-Agent": "WalletRiskAnalyzer/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        return data["result"] if data.get("status") == "1" and data.get("result") else []
    except Exception:
        return []


def analyze_risks(address: str) -> dict:
    risks = []
    balance = get_balance(address)
    tx_count = get_tx_count(address)
    code = get_code(address)
    is_contract = code != "0x" and len(code) > 2
    eth_price = get_eth_price()

    info = {
        "address": address,
        "balance_eth": balance,
        "balance_usd": round(balance * eth_price.get("usd", 0), 2),
        "balance_cny": round(balance * eth_price.get("cny", 0), 2),
        "tx_count": tx_count,
        "is_contract": is_contract,
        "eth_price_usd": eth_price.get("usd", 0),
        "eth_price_cny": eth_price.get("cny", 0),
        "scan_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S CST"),
    }

    if balance == 0 and tx_count == 0:
        risks.append({"level": "INFO", "category": "Wallet Status", "detail": "Zero balance and no transactions — new or inactive address", "action": "No action needed"})
    if is_contract:
        risks.append({"level": "Warning", "category": "Address Type", "detail": "Contract address, not EOA — may have custom logic", "action": "Review contract source code"})

    recent_txs = get_recent_txs_etherscan(address, 20)
    info["recent_tx_count"] = len(recent_txs)

    for tx in recent_txs:
        if tx.get("isError") == "1":
            risks.append({"level": "INFO", "category": "Failed Transaction", "detail": f"Failed tx: {tx.get('hash', '')[:20]}...", "action": "Check gas or contract revert reason"})
        gas_used = int(tx.get("gasUsed", "0"))
        if gas_used > 500000:
            risks.append({"level": "Warning", "category": "High Gas", "detail": f"High gas tx ({gas_used} gas): {tx.get('hash', '')[:20]}...", "action": "Review interaction complexity"})

    token_txs = get_erc20_transfers_etherscan(address, 20)
    info["token_tx_count"] = len(token_txs)
    info["interacted_tokens"] = list(set(t.get("tokenName", "Unknown") for t in token_txs))[:20]

    internal_txs = get_internal_txs_etherscan(address, 10)
    info["internal_tx_count"] = len(internal_txs)

    if recent_txs:
        latest_time = int(recent_txs[0].get("timeStamp", "0"))
        days_since = (datetime.datetime.now().timestamp() - latest_time) / 86400
        info["days_since_last_tx"] = round(days_since, 1)
        if days_since > 365:
            risks.append({"level": "INFO", "category": "Activity", "detail": f"Dormant for {round(days_since)} days", "action": "Confirm if still primary wallet"})

    info["risks"] = risks
    return info


def generate_html_report(info: dict) -> str:
    risk_html = ""
    for risk in info.get("risks", []):
        color = {"Warning": "#ff8800", "INFO": "#4488ff"}.get(risk["level"], "#888")
        risk_html += f'<div style="border-left:4px solid {color};padding:12px;margin:8px 0;background:#1a1a2e;border-radius:0 8px 8px 0;"><div style="font-weight:bold;color:{color};">[{risk["level"]}] {risk["category"]}</div><div style="color:#ccc;margin-top:4px;">{risk["detail"]}</div><div style="color:#aaa;margin-top:4px;">{risk["action"]}</div></div>'

    tokens_html = "".join(f'<span style="background:#2a2a4a;padding:4px 10px;border-radius:12px;margin:2px;display:inline-block;font-size:13px;">{t}</span> ' for t in info.get("interacted_tokens", [])[:10])

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Wallet Risk Audit</title><style>body{{background:#0d1117;color:#e6edf3;font-family:-apple-system,sans-serif;padding:20px;max-width:800px;margin:0 auto}}h1{{color:#58a6ff;border-bottom:2px solid #30363d;padding-bottom:12px}}.card{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:20px;margin:12px 0}}.stat{{display:inline-block;text-align:center;padding:12px 20px}}.stat-value{{font-size:24px;font-weight:bold;color:#58a6ff}}.stat-label{{font-size:12px;color:#8b949e}}</style></head><body>
<h1>🔗 Wallet Risk Audit Report</h1><p style="color:#8b949e;">📅 {info['scan_time']} | ETH ${info['eth_price_usd']:,.2f} / ¥{info['eth_price_cny']:,.2f}</p>
<div class="card"><code style="color:#58a6ff;word-break:break-all;">{info['address']}</code></div>
<div class="card" style="text-align:center"><div class="stat"><div class="stat-value">{info['balance_eth']:.4f}</div><div class="stat-label">ETH</div></div><div class="stat"><div class="stat-value">${info['balance_usd']:,.2f}</div><div class="stat-label">USD</div></div><div class="stat"><div class="stat-value">¥{info['balance_cny']:,.2f}</div><div class="stat-label">CNY</div></div><div class="stat"><div class="stat-value">{info['tx_count']}</div><div class="stat-label">Txns</div></div><div class="stat"><div class="stat-value">{'Contract' if info['is_contract'] else 'EOA'}</div><div class="stat-label">Type</div></div></div>
<div class="card"><h2>⚠️ Risk Assessment</h2>{risk_html or '<p style="color:#3fb950;">✅ No significant risks found</p>'}</div>
{f'<div class="card"><h2>🪙 Tokens</h2>{tokens_html}</div>' if tokens_html else ''}
<div class="card"><h2>🛡️ Safety Tips</h2><ol><li>Revoke unnecessary approvals at <a href="https://revoke.cash" style="color:#58a6ff;">revoke.cash</a></li><li>Don't interact with unverified contracts</li><li>Use hardware wallets for large holdings</li><li>Beware of phishing and fake airdrops</li><li>Test with small amounts first</li></ol></div>
<div style="background:#1c1e24;border:1px solid #f0883e33;border-radius:8px;padding:16px;margin-top:24px;font-size:13px;color:#8b949e;"><strong>⚠️ Disclaimer:</strong> Based on public on-chain data. Not financial advice. No private keys or sensitive data accessed.</div>
<div style="text-align:center;margin-top:24px;padding:16px;background:#161b22;border:1px solid #30363d;border-radius:8px;"><p style="color:#58a6ff;font-size:14px;">Need a deeper security audit for your Web3 project?</p><p style="color:#8b949e;font-size:13px;">This tool is built by <a href="https://richard202605.github.io/web3-docs-service/" style="color:#58a6ff;">FlowForge AI Ops</a> — Web3 documentation and security audit services ($200-$2,000)</p></div>
<p style="text-align:center;color:#484f58;margin-top:32px;font-size:12px;">Powered by FlowForge AI Ops | Wallet Risk Analyzer v1.0</p></body></html>"""


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 wallet_risk_analyzer.py <ethereum_address> [--output-dir DIR]")
        sys.exit(1)

    address = sys.argv[1].strip()
    if not address.startswith("0x") or len(address) != 42:
        print(f"❌ Invalid address: {address}")
        sys.exit(1)

    output_dir = DEFAULT_REPORT_DIR
    if "--output-dir" in sys.argv:
        idx = sys.argv.index("--output-dir")
        if idx + 1 < len(sys.argv):
            output_dir = sys.argv[idx + 1]

    print(f"🔍 Analyzing: {address}")
    info = analyze_risks(address)

    # Terminal output
    print(f"\n{'='*60}\n🔗 Wallet Risk Audit\n{'='*60}")
    print(f"📅 {info['scan_time']}\n📍 {info['address']}")
    print(f"💰 {info['balance_eth']:.4f} ETH (${info['balance_usd']:,.2f} / ¥{info['balance_cny']:,.2f})")
    print(f"📊 {info['tx_count']} txns | {'Contract' if info['is_contract'] else 'EOA'}")
    for risk in info.get("risks", []):
        print(f"  [{risk['level']}] {risk['category']}: {risk['detail']}")

    # Save files
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = address[:10].replace("0x", "0x")

    html_path = os.path.join(output_dir, f"audit_{prefix}_{ts}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(generate_html_report(info))

    json_path = os.path.join(output_dir, f"audit_{prefix}_{ts}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    print(f"\n📄 HTML: {html_path}")
    print(f"📊 JSON: {json_path}")
    return info


if __name__ == "__main__":
    main()
