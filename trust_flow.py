"""
Wallet Trust Profiles — Agent-to-Agent Trust Signals

Generate ECDSA-signed trust fact profiles for any EVM wallet.
145 base checks across 27 chains in 9 dimensions (up to 166 checks across 29 chains
in 13 dimensions with optional non-EVM wallets). Every check is a presence check:
  - Stablecoins (52): USDC, USDT, OUSD, PYUSD, USDG, USD1, RLUSD, USDS, DAI, EURC across 23 EVM chains
  - Governance (8): UNI, AAVE, ARB, OP, ENS, LDO, SKY, COMP
  - NFTs (3): BAYC, Pudgy Penguins, Wrapped CryptoPunks
  - Staking (5): stETH, rETH, cbETH, wstETH, weETH
  - Institutional stablecoins (8): EURCV, USDCV, USDC and BENJI
  - Tokenized treasuries (16): BUIDL, USYC, OUSG, USTB, USDY
  - Stablecoin deposits (39): Aave v3 aUSDC/aUSDT, sUSDS, sDAI, Morpho USDC vaults
  - Wrapped bitcoin (12): cbBTC, WBTC, tBTC
  - Names (2): ENS .eth, Basenames
  - Optional: Solana (14), XRPL (3), Bitcoin (1), Tron (3)
conditionSetVersion (currently "2026-10") is signed and names the check list run.

Single wallet (3 credits) or batch up to 10 wallets (3 credits/wallet).
Batch mode shares block fetches for 5-8x faster throughput.

Usage:
    export INSUMER_API_KEY="insr_live_YOUR_KEY_HERE"
    python trust_flow.py
"""

import os
import sys
import requests

BASE_URL = "https://api.insumermodel.com"
API_KEY = os.environ.get("INSUMER_API_KEY", "")

if not API_KEY:
    print("Set INSUMER_API_KEY environment variable first.")
    print("Get a free key: https://insumermodel.com/developers/#pricing")
    sys.exit(1)

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


# ── Example 1: Single wallet trust profile ───────────────────────

print("=== Single Wallet Trust Profile ===\n")

result = requests.post(
    f"{BASE_URL}/v1/trust",
    headers=HEADERS,
    json={
        "wallet": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        "xrplWallet": "rG1QQv2nh2gr7RCZ1P8YYcBUKCCN633jCn",
    },
).json()

if not result["ok"]:
    # rpc_failure (503) = data source unavailable, retryable after 2-5s
    if result.get("error", {}).get("code") == "rpc_failure":
        print("rpc_failure: data source temporarily unavailable — retry after 2-5s")
        for fc in result["error"].get("failedConditions", []):
            print(f"  chain {fc.get('chainId', '?')}: {fc['message']}")
    else:
        print(f"Error: {result['error']['message']}")
    sys.exit(1)

trust = result["data"]["trust"]
summary = trust["summary"]

print(f"Profile ID: {trust['id']}")
print(f"Wallet:     {trust['wallet']}")
print(f"Version:    {trust['conditionSetVersion']}")
print(f"Profiled:   {trust['profiledAt']}")
print(f"Expires:    {trust['expiresAt']}")

print(f"\nSummary: {summary['totalPassed']}/{summary['totalChecks']} checks passed")
print(f"Active dimensions: {summary['dimensionsWithActivity']}/{summary['dimensionsChecked']}")

for dim_name, dim_data in trust["dimensions"].items():
    passed = dim_data["passCount"]
    total = dim_data["total"]
    status = "active" if passed > 0 else "empty"
    print(f"\n  {dim_name.upper()} ({status}): {passed}/{total} passed")

    for check in dim_data["checks"][:3]:  # show first 3
        if check.get("evaluated") is False:
            print(f"    [NOT EVALUATED (requires {check.get('requires')})] {check['label']} (chain {check['chainId']})")
            continue
        icon = "PASS" if check["met"] else "FAIL"
        print(f"    [{icon}] {check['label']} (chain {check['chainId']})")

    if len(dim_data["checks"]) > 3:
        print(f"    ... and {len(dim_data['checks']) - 3} more")

print(f"\nSigned: kid={result['data']['kid']}")
print(f"Sig:    {result['data']['sig'][:40]}...")
print(f"Credits: {result['meta']['creditsCharged']} used, {result['meta']['creditsRemaining']} remaining")


# ── Example 2: Batch trust profiles ──────────────────────────────

print("\n\n=== Batch Trust Profiles (3 wallets) ===\n")

wallets = [
    {"wallet": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"},  # vitalik.eth
    {"wallet": "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B"},  # another known wallet
    {"wallet": "0x1234567890abcdef1234567890abcdef12345678",
     "xrplWallet": "rG1QQv2nh2gr7RCZ1P8YYcBUKCCN633jCn"},  # with XRPL
]

batch = requests.post(
    f"{BASE_URL}/v1/trust/batch",
    headers=HEADERS,
    json={"wallets": wallets},
).json()

if not batch["ok"]:
    print(f"Error: {batch['error']['message']}")
    sys.exit(1)

results = batch["data"]["results"]

for i, entry in enumerate(results):
    if "error" in entry:
        print(f"Wallet {i + 1}: ERROR — {entry['error']}")
        continue

    t = entry["trust"]
    s = t["summary"]
    print(f"Wallet {i + 1}: {t['wallet'][:10]}...{t['wallet'][-4:]}")
    print(f"  ID: {t['id']} | {s['totalPassed']}/{s['totalChecks']} passed | {s['dimensionsWithActivity']} active dims")

print(f"\nBatch credits: {batch['meta']['creditsCharged']} used ({batch['meta']['creditsCharged'] // len(wallets)}/wallet)")
print(f"Credits remaining: {batch['meta']['creditsRemaining']}")
