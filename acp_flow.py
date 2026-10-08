"""
ACP Discount Flow — OpenAI/Stripe Agentic Commerce Protocol

Verifies on-chain token holdings and returns the discount in ACP format
with coupon objects, an applied array, and per-item allocations.

The INSR-XXXXX redemption code is in data["verification"]["code"].
discounts.codes and discounts.rejected are always empty on this endpoint:
they echo discount codes the caller submitted, and it accepts none.
An applied entry needs a monetary base, so pass items[] or subtotal
(minor units); without either, applied is empty even for an eligible wallet.

A code that carries a discount costs 1 credit from the API key that owns
the store; a 0% result is free, and a caller using another key is not charged.

By default the example runs against demo-coffee-shop, InsumerAPI's demo
store, which pays for its own codes. Set INSUMER_MERCHANT_ID to run it
against a store your key owns (create one with merchant_onboarding.py).

Usage:
    export INSUMER_API_KEY="insr_live_YOUR_KEY_HERE"
    export INSUMER_MERCHANT_ID="your-merchant-id"   # optional
    python acp_flow.py
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


def acp_discount(
    merchant_id: str,
    wallet: str | None = None,
    solana_wallet: str | None = None,
    xrpl_wallet: str | None = None,
    items: list | None = None,
    subtotal: int | None = None,
) -> dict:
    """Request an ACP-format discount for a wallet at a merchant."""
    payload = {"merchantId": merchant_id}
    if wallet:
        payload["wallet"] = wallet
    if solana_wallet:
        payload["solanaWallet"] = solana_wallet
    if xrpl_wallet:
        payload["xrplWallet"] = xrpl_wallet
    if items:
        payload["items"] = items
    elif subtotal is not None:
        payload["subtotal"] = subtotal

    resp = requests.post(
        f"{BASE_URL}/v1/acp/discount",
        headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
        json=payload,
    )
    result = resp.json()
    # rpc_failure (503) = data source unavailable, retryable after 2-5s
    if resp.status_code == 503 and result.get("error", {}).get("code") == "rpc_failure":
        print("  rpc_failure: data source temporarily unavailable — retry after 2-5s")
    return result


# --- Example 1: Basic ACP discount ---

print("=== Basic ACP Discount ===\n")

# For XRPL wallets, pass xrpl_wallet instead of wallet:
#   acp_discount(merchant_id=MERCHANT_ID, xrpl_wallet="rG1QQv2nh2gr7RCZ1P8YYcBUKCCN633jCn")

result = acp_discount(
    merchant_id=MERCHANT_ID,
    wallet="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    subtotal=5000,  # $50.00 order, in cents
)

if not result["ok"]:
    print(f"Error: {result['error']['message']}")
    sys.exit(1)

discounts = result["data"]["discounts"]

verification = result["data"]["verification"]

if discounts["applied"]:
    entry = discounts["applied"][0]
    coupon = entry["coupon"]

    print(f"Discount: {coupon['percent_off']}% off (${entry['amount'] / 100:.2f})")
    print(f"Coupon:   {coupon['name']}")
    print(f"Code:     {verification['code']}")
    print(f"Expires:  {entry['end']}")
    print(f"Signed:   {verification['sig'][:40]}...")
else:
    print("Not eligible: this wallet holds nothing the merchant discounts.")

print(f"\nCredits used: {result['meta']['creditsCharged']}")
print(f"Credits left: {result['meta']['creditsRemaining']}")


# --- Example 2: ACP with per-item allocations ---

print("\n\n=== ACP with Per-Item Allocations ===\n")

result = acp_discount(
    merchant_id=MERCHANT_ID,
    wallet="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    items=[
        {"path": "cart/espresso", "amount": 450},
        {"path": "cart/croissant", "amount": 350},
        {"path": "cart/water", "amount": 200},
    ],
)

if result["ok"] and result["data"]["discounts"]["applied"]:
    entry = result["data"]["discounts"]["applied"][0]
    print(f"Total discount: ${entry.get('amount', 0) / 100:.2f}")

    if "allocations" in entry:
        print("Per-item breakdown:")
        for alloc in entry["allocations"]:
            print(f"  {alloc['path']}: -${alloc['amount'] / 100:.2f}")
elif result["ok"]:
    print("Not eligible: this wallet holds nothing the merchant discounts.")
else:
    print(f"Error: {result['error']['message']}")
