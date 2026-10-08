"""
UCP Discount Flow — Google Universal Commerce Protocol

Verifies on-chain token holdings and returns the discount in UCP format
with title strings, the dev.ucp.shopping.discount extension, and
per-item allocations.

A code that carries a discount costs 1 credit from the API key that owns
the store; a 0% result is free, and a caller using another key is not charged.

By default the example runs against demo-coffee-shop, InsumerAPI's demo
store, which pays for its own codes. Set INSUMER_MERCHANT_ID to run it
against a store your key owns (create one with merchant_onboarding.py).

Usage:
    export INSUMER_API_KEY="insr_live_YOUR_KEY_HERE"
    export INSUMER_MERCHANT_ID="your-merchant-id"   # optional
    python ucp_flow.py
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

# demo-coffee-shop is InsumerAPI's demo store; set INSUMER_MERCHANT_ID for your own.
MERCHANT_ID = os.environ.get("INSUMER_MERCHANT_ID", "demo-coffee-shop")
print(f"Merchant: {MERCHANT_ID}\n")


def ucp_discount(
    merchant_id: str,
    wallet: str | None = None,
    solana_wallet: str | None = None,
    xrpl_wallet: str | None = None,
    items: list | None = None,
) -> dict:
    """Request a UCP-format discount for a wallet at a merchant."""
    payload = {"merchantId": merchant_id}
    if wallet:
        payload["wallet"] = wallet
    if solana_wallet:
        payload["solanaWallet"] = solana_wallet
    if xrpl_wallet:
        payload["xrplWallet"] = xrpl_wallet
    if items:
        payload["items"] = items

    resp = requests.post(
        f"{BASE_URL}/v1/ucp/discount",
        headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
        json=payload,
    )
    result = resp.json()
    # rpc_failure (503) = data source unavailable, retryable after 2-5s
    if resp.status_code == 503 and result.get("error", {}).get("code") == "rpc_failure":
        print("  rpc_failure: data source temporarily unavailable — retry after 2-5s")
    return result


# --- Example: UCP discount with items ---

print("=== UCP Discount ===\n")

# For XRPL wallets, pass xrpl_wallet instead of wallet:
#   ucp_discount(merchant_id=MERCHANT_ID, xrpl_wallet="rG1QQv2nh2gr7RCZ1P8YYcBUKCCN633jCn")

result = ucp_discount(
    merchant_id=MERCHANT_ID,
    wallet="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    items=[
        {"path": "cart/espresso", "amount": 450},
        {"path": "cart/pastry", "amount": 350},
    ],
)

if not result["ok"]:
    print(f"Error: {result['error']['message']}")
    sys.exit(1)

data = result["data"]

# UCP-specific fields
print(f"Protocol:  {data['protocol']}")
print(f"Version:   {data['version']}")
print(f"Extension: {data['extension']}")

applied = data["discounts"]["applied"]
if applied:
    discount = applied[0]
    # Applied entries are automatic discounts and carry no `code`; the
    # INSR-XXXXX redemption code is in `verification`.
    code = data["verification"]["code"]
    title = discount["title"]

    print(f"\nTitle:     {title}")
    print(f"Code:      {code}")

    if "amount" in discount:
        print(f"Savings:   ${discount['amount'] / 100:.2f}")

    if "allocations" in discount:
        print("\nPer-item allocations:")
        for alloc in discount["allocations"]:
            print(f"  {alloc['path']}: -${alloc['amount'] / 100:.2f}")

    # Verification data
    verification = data["verification"]
    print(f"\nExpires:   {verification['expiresAt']}")
    print(f"Key ID:    {verification['kid']}")
    print(f"Signature: {verification['sig'][:40]}...")
else:
    print("No discount available for this wallet.")

print(f"\nCredits used: {result['meta']['creditsCharged']}")
print(f"Credits left: {result['meta']['creditsRemaining']}")


# --- UCP Discovery ---

print("\n\n=== UCP Discovery ===\n")
print("UCP agents discover InsumerAPI automatically:")
print("GET https://insumermodel.com/.well-known/ucp.json")

discovery = requests.get("https://insumermodel.com/.well-known/ucp.json").json()
print(f"\nProvider:     {discovery['name']}")
print(f"Capabilities: {discovery['capabilities']}")
print(f"Discount:     {discovery['endpoints']['discount']['method']} {discovery['endpoints']['discount']['path']}")
print(f"Validation:   {discovery['endpoints']['validate_code']['method']} {discovery['endpoints']['validate_code']['path']}")
