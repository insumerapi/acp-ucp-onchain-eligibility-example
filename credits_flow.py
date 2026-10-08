"""
Credit Management — Check Balance and Buy Credits On-Chain

Agents can autonomously manage their API credits:
  - Check current balance and tier
  - Buy verification credits with USDC, USDT or BTC (minimum $5).
    Volume rates: $5-99 = 25 credits per $1, $100-499 = 33 per $1,
    $500+ = 50 per $1

One credit balance: the same credits pay for discount codes at any store
your key owns. A code that carries a discount costs 1 credit from the key
that owns the store (a 0% result is free); a caller using another key is
not charged. A store has no balance of its own.

Accepted payments (the token is detected from the transaction):
  USDC or USDT on Ethereum (1), Base (8453), Polygon (137), Arbitrum (42161),
  Optimism (10), BNB Chain (56), Avalanche (43114) and Solana ("solana")
  USDT (TRC-20) on Tron ("tron")
  BTC on Bitcoin ("bitcoin"), credited at the transfer's USD value

Platform wallets:
  EVM:     0xAd982CB19aCCa2923Df8F687C0614a7700255a23
  Solana:  6a1mLjefhvSJX1sEX8PTnionbE9DqoYjU6F6bNkT4Ydr
  Tron:    TC5yvwkAMakkXtUxYiu2Yn1xbBcwYuD6cn
  Bitcoin: bc1qg7qnerdhlmdn899zemtez5tcx2a2snc0dt9dt0

Usage:
    export INSUMER_API_KEY="insr_live_YOUR_KEY_HERE"
    python credits_flow.py
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


# ── Step 1: Check current credit balance ─────────────────────────

print("=== Step 1: Check Credit Balance ===\n")

result = requests.get(f"{BASE_URL}/v1/credits", headers=HEADERS).json()

if result["ok"]:
    data = result["data"]
    print(f"  Credits:     {data['apiKeyCredits']}")
    print(f"  Tier:        {data['tier']}")
    print(f"  Daily limit: {data['dailyLimit']} requests/day")

    # Pricing reference
    print("\n  Pricing:")
    print("    Attestation:       1 credit  ($0.04)")
    print("    Attestation+proof: 2 credits ($0.08)")
    print("    Trust profile:     3 credits ($0.12)")
    print("    Trust+proof:       6 credits ($0.24)")
    print("    Discount code:     1 credit from the store owner's key (0% result free)")
else:
    print(f"  Error: {result['error']['message']}")
    sys.exit(1)


# ── Step 2: Buy verification credits on-chain ───────────────────

print("\n=== Step 2: Buy Verification Credits (USDC, USDT or BTC) ===\n")
print("To buy credits, send USDC, USDT or BTC to the platform wallet and submit the tx hash.\n")

# This example shows the API call structure.
# In production, your agent would:
#   1. Send USDC, USDT or BTC on-chain to the platform wallet
#   2. Get the transaction hash
#   3. Submit it here for credit top-up

EXAMPLE_TX = "0x0000000000000000000000000000000000000000000000000000000000000000"

print("  Example API call (dry run — use a real tx hash in production):\n")
print(f"  POST {BASE_URL}/v1/credits/buy")
print(f"  Body: {{")
print(f'    "txHash": "{EXAMPLE_TX}",')
print(f'    "chainId": 8453,   // Base')
print(f'    "amount": 5         // 5 USDC or USDT = 125 credits')
print(f"  }}")

print("\n  Platform wallets:")
print("    EVM:     0xAd982CB19aCCa2923Df8F687C0614a7700255a23")
print("    Solana:  6a1mLjefhvSJX1sEX8PTnionbE9DqoYjU6F6bNkT4Ydr")
print("    Tron:    TC5yvwkAMakkXtUxYiu2Yn1xbBcwYuD6cn")
print("    Bitcoin: bc1qg7qnerdhlmdn899zemtez5tcx2a2snc0dt9dt0")

print("\n  Supported chains:")
chains = [
    ("Ethereum", 1, "USDC or USDT"), ("Base", 8453, "USDC or USDT"),
    ("Polygon", 137, "USDC or USDT"), ("Arbitrum", 42161, "USDC or USDT"),
    ("Optimism", 10, "USDC or USDT"), ("BNB Chain", 56, "USDC or USDT"),
    ("Avalanche", 43114, "USDC or USDT"), ("Solana", "solana", "USDC or USDT"),
    ("Tron", "tron", "USDT (TRC-20)"), ("Bitcoin", "bitcoin", "BTC"),
]
for name, chain_id, tokens in chains:
    print(f"    {name} (chainId: {chain_id}): {tokens}")

print("\n  Rates: $5-99 = 25 credits per $1 | $100-499 = 33 per $1 | $500+ = 50 per $1")
print("  Minimum: $5 (125 credits). BTC is credited at the transfer's USD value.")


# ── Step 3: Top up through a store you own (compatibility) ──────

print("\n\n=== Step 3: Store Top-Up Endpoint (Compatibility) ===\n")
print("A store has no credit balance of its own. Its discount codes (/v1/verify,")
print("/v1/acp/discount, /v1/ucp/discount) are paid from the API key that owns it,")
print("the same balance POST /v1/credits/buy tops up.\n")

MERCHANT_ID = "your-merchant-id"

print(f"  Example API call (kept for compatibility; owner key only):")
print(f"  POST {BASE_URL}/v1/merchants/{MERCHANT_ID}/credits")
print(f"  Body: {{")
print(f'    "txHash": "0x...",')
print(f'    "chainId": 8453,')
print(f'    "amount": 10        // 10 USDC or USDT = 250 credits on the owner key (flat 25 per $1)')
print(f"  }}")
print("\n  Use POST /v1/credits/buy instead: same balance, with the volume rates.")


# ── Autonomous agent flow ────────────────────────────────────────

print("\n\n=== Full Autonomous Credit Management Flow ===\n")
print("An agent can maintain its own credit balance without human intervention:\n")
print("  1. GET  /v1/credits           — check remaining credits")
print("  2. If low, send USDC, USDT or BTC on-chain — agent initiates transfer")
print("  3. POST /v1/credits/buy       — submit tx hash, receive credits")
print("  4. Continue making API calls   — attestations, trust profiles, discounts")
print("\nThe same balance pays for discount codes at the stores your key owns.")
print("\nThis enables fully autonomous agent commerce with no human billing cycle.")
