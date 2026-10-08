"""
Full Agent Commerce Flow — End-to-End

Complete flow an AI agent follows:
  1. Discover merchants from the directory
  2. Check discount eligibility (free)
  3. Request a signed discount code (ACP or UCP)
  4. Validate the code at merchant checkout

Step 3 issues a real code. A code that carries a discount costs 1 credit
from the API key that owns the store. By default the flow runs against
demo-coffee-shop, InsumerAPI's demo store, which pays for its own codes.
Set INSUMER_MERCHANT_ID to run it against a store your key owns (create
one with merchant_onboarding.py).

Usage:
    export INSUMER_API_KEY="insr_live_YOUR_KEY_HERE"
    export INSUMER_MERCHANT_ID="your-merchant-id"   # optional
    python full_agent_flow.py
"""

import os
import sys
import requests

BASE_URL = "https://api.insumermodel.com"
API_KEY = os.environ.get("INSUMER_API_KEY", "")
WALLET = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

if not API_KEY:
    print("Set INSUMER_API_KEY environment variable first.")
    print("Get a free key: https://insumermodel.com/developers/#pricing")
    sys.exit(1)

# demo-coffee-shop is InsumerAPI's demo store; set INSUMER_MERCHANT_ID for your own.
MERCHANT_ID = os.environ.get("INSUMER_MERCHANT_ID", "demo-coffee-shop")


# ── Step 1: Discover merchants ──────────────────────────────────

print("=== Step 1: Discover Merchants ===\n")

merchants = requests.get(
    f"{BASE_URL}/v1/merchants",
    headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
    params={"verified": "true", "limit": 5},
).json()

if merchants["ok"]:
    for m in merchants["data"]:
        tokens = [t["symbol"] for t in m.get("tokens", [])]
        print(f"  {m['companyName']} ({m['id']}), tokens: {', '.join(tokens) or 'none'}")
    if not merchants["data"]:
        print("  No verified merchants listed.")

merchant_id = MERCHANT_ID
print(f"\nUsing merchant: {merchant_id}")


# ── Step 2: Check eligibility (free) ────────────────────────────

print("\n=== Step 2: Check Eligibility (Free) ===\n")

eligibility = requests.get(
    f"{BASE_URL}/v1/discount/check",
    headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
    params={"merchant": merchant_id, "wallet": WALLET},
).json()

if eligibility["ok"]:
    elig = eligibility["data"]
    print(f"Eligible: {elig.get('eligible', False)}")
    if elig.get("eligible"):
        print(f"Discount: {elig.get('totalDiscount', 0)}%")
    else:
        print("Wallet does not qualify for this merchant.")
        print("(Try a different merchant or wallet)")
elif eligibility.get("error", {}).get("code") == "rpc_failure":
    # rpc_failure (503) = a read did not complete. Nothing is concluded about
    # the wallet: this is not "not eligible". Retryable after 2-5s.
    print("rpc_failure: data source temporarily unavailable. Retry after 2-5s.")
    for fc in eligibility["error"].get("failedConditions", []):
        print(f"  chain {fc.get('chainId', '?')}: {fc['message']}")
    sys.exit(1)
else:
    print(f"Error: {eligibility['error']['message']}")


# ── Step 3: Request ACP discount ────────────────────────────────

print("\n=== Step 3: Request ACP Discount ===\n")

cart_items = [
    {"path": "cart/item-1", "amount": 2500},
    {"path": "cart/item-2", "amount": 1500},
]

acp = requests.post(
    f"{BASE_URL}/v1/acp/discount",
    headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
    json={
        "merchantId": merchant_id,
        "wallet": WALLET,
        "items": cart_items,
    },
).json()

if not acp["ok"]:
    # rpc_failure (503) = data source unavailable, retryable after 2-5s
    if acp.get("error", {}).get("code") == "rpc_failure":
        print("rpc_failure: data source temporarily unavailable — retry after 2-5s")
        for fc in acp["error"].get("failedConditions", []):
            print(f"  chain {fc.get('chainId', '?')}: {fc['message']}")
    else:
        print(f"Error: {acp['error']['message']}")
    sys.exit(1)

applied = acp["data"]["discounts"]["applied"]

if not applied:
    print("Not eligible: this wallet holds nothing the merchant discounts.")
    sys.exit(0)

coupon = applied[0]["coupon"]
# The INSR-XXXXX redemption code travels in `verification`; discounts.codes
# only echoes codes the caller submitted, and this endpoint accepts none.
code = acp["data"]["verification"]["code"]

print(f"Discount: {coupon['percent_off']}% off")
print(f"Coupon:   {coupon['name']}")
print(f"Code:     {code}")
print(f"Expires:  {applied[0]['end']}")

if "allocations" in applied[0]:
    print("\nPer-item savings:")
    for alloc in applied[0]["allocations"]:
        print(f"  {alloc['path']}: -${alloc['amount'] / 100:.2f}")

# Verification data
verification = acp["data"]["verification"]
print(f"\nSigned by: kid={verification['kid']}")
print(f"Signature: {verification['sig'][:40]}...")
print(f"Credits remaining: {acp['meta']['creditsRemaining']}")


# ── Step 4: Merchant validates the code ─────────────────────────

print(f"\n=== Step 4: Validate Code ({code}) ===\n")

validation = requests.get(f"{BASE_URL}/v1/codes/{code}").json()

if validation["ok"] and validation["data"]["valid"]:
    v = validation["data"]
    print(f"VALID")
    print(f"  Merchant:  {v['merchantId']}")
    print(f"  Discount:  {v['discountPercent']}%")
    print(f"  Expires:   {v['expiresAt']}")

    # Calculate final total
    cart_total = sum(item["amount"] for item in cart_items)
    savings = cart_total * v["discountPercent"] // 100
    final = cart_total - savings

    print(f"\n  Cart total:  ${cart_total / 100:.2f}")
    print(f"  Savings:     -${savings / 100:.2f}")
    print(f"  Final total: ${final / 100:.2f}")
elif validation["ok"]:
    print(f"INVALID: {validation['data']['reason']}")
else:
    print(f"Error: {validation['error']['message']}")
