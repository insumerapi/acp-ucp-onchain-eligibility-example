"""
Autonomous Merchant Onboarding — Full Self-Serve Pipeline

An AI agent can onboard a merchant end-to-end with zero human intervention:
  1. Create merchant (owned by your API key, which pays for its discount codes)
  2. Configure token discount tiers (up to 8 tokens, 4 tiers each)
  3. Configure NFT collections (up to 4)
  4. Set discount mode and USDC payment settings
  5. Publish to public directory
  6. Check full merchant status

This is the complete autonomous commerce setup flow.

Usage:
    export INSUMER_API_KEY="insr_live_YOUR_KEY_HERE"
    export MERCHANT_EVM_ADDRESS="0xYourStoreWallet"   # where YOUR customers pay you
    python merchant_onboarding.py
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

# The merchant's own receiving wallet: shoppers are told to pay this address.
# There is deliberately no default. Use a wallet you control; never copy one
# from an example.
MERCHANT_EVM_ADDRESS = os.environ.get("MERCHANT_EVM_ADDRESS", "")

if not MERCHANT_EVM_ADDRESS:
    print("Set MERCHANT_EVM_ADDRESS to the wallet where your customers should pay you.")
    sys.exit(1)

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# Unique merchant ID for this example (change to avoid conflicts)
MERCHANT_ID = "agent-onboarded-demo"


# ── Step 1: Create merchant ──────────────────────────────────────

print("=== Step 1: Create Merchant ===\n")

result = requests.post(
    f"{BASE_URL}/v1/merchants",
    headers=HEADERS,
    json={
        "companyName": "Agent Onboarded Coffee",
        "companyId": MERCHANT_ID,
        "location": "San Francisco, CA",
    },
).json()

if result["ok"]:
    print(f"  Created: {result['data']['companyName']}")
    print(f"  ID:      {result['data']['id']}")
    print(f"  Credits: {result['data']['credits']} (your key's balance; the store has none of its own)")
elif result["error"]["code"] == 409:
    print(f"  Merchant '{MERCHANT_ID}' already exists (continuing with config)")
else:
    print(f"  Error: {result['error']['message']}")
    sys.exit(1)


# ── Step 2: Configure token tiers ────────────────────────────────

print("\n=== Step 2: Configure Token Discount Tiers ===\n")

result = requests.put(
    f"{BASE_URL}/v1/merchants/{MERCHANT_ID}/tokens",
    headers=HEADERS,
    json={
        "ownToken": {
            "symbol": "UNI",
            "chainId": 1,
            "contractAddress": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
            "decimals": 18,
            "tiers": [
                {"name": "Bronze", "threshold": 10, "discount": 5},
                {"name": "Silver", "threshold": 100, "discount": 10},
                {"name": "Gold", "threshold": 1000, "discount": 15},
                {"name": "Diamond", "threshold": 10000, "discount": 20},
            ],
        },
        "partnerTokens": [
            {
                "symbol": "USDC",
                "chainId": 8453,
                "contractAddress": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                "decimals": 6,
                "tiers": [
                    {"name": "Holder", "threshold": 100, "discount": 3},
                    {"name": "Whale", "threshold": 10000, "discount": 8},
                ],
            },
            {
                "symbol": "RLUSD",
                "chainId": "xrpl",
                "contractAddress": "rMxCKbEDwqr76QuheSUMdEGf4B9xJ8m5De",
                # XRPL stores currency codes longer than 3 characters as 40 hex
                # characters, and account balances are matched on that code, so
                # "RLUSD" is written the way the ledger writes it.
                "currency": "524C555344000000000000000000000000000000",
                # Required (0-18) on every token config. XRPL trust-line balances
                # are ledger decimal strings, not integer-scaled, so this value
                # is not used to scale the balance; 15 matches XRPL's 15
                # significant digits for issued currencies.
                "decimals": 15,
                "tiers": [
                    {"name": "Holder", "threshold": 100, "discount": 3},
                    {"name": "Whale", "threshold": 10000, "discount": 8},
                ],
            },
        ],
    },
).json()

if result["ok"]:
    data = result["data"]
    print(f"  Own token: {data['ownToken']['symbol']} ({data['ownToken']['tiersConfigured']} tiers)")
    print(f"  Partner tokens: {len(data['partnerTokens'])}")
    print(f"  Total: {data['totalTokens']}/{data['maxTokens']} token slots used")
else:
    print(f"  Error: {result['error']['message']}")


# ── Step 3: Configure NFT collections ────────────────────────────

print("\n=== Step 3: Configure NFT Collections ===\n")

result = requests.put(
    f"{BASE_URL}/v1/merchants/{MERCHANT_ID}/nfts",
    headers=HEADERS,
    json={
        "nftCollections": [
            {
                "name": "Pudgy Penguins",
                "contractAddress": "0xBd3531dA5CF5857e7CfAA92426877b022e612cf8",
                "chainId": 1,
                "discount": 12,
            },
            {
                "name": "Base Onchain Summer",
                "contractAddress": "0xD4307E0acD12CF46fD6cf93BC264f5D5D1598792",
                "chainId": 8453,
                "discount": 8,
            },
            {
                "name": "XRPL NFT Collection",
                "contractAddress": "rUDRQfn1hr84kVqQ42BoLgBsLtRgMWD4k5",
                "chainId": "xrpl",
                "discount": 5,
            },
        ],
    },
).json()

if result["ok"]:
    data = result["data"]
    for nft in data["nftCollections"]:
        print(f"  {nft['name']}: {nft['discount']}% off")
    print(f"  Total: {data['totalCollections']}/{data['maxCollections']} NFT slots used")
else:
    print(f"  Error: {result['error']['message']}")


# ── Step 4: Set discount mode and USDC payments ─────────────────

print("\n=== Step 4: Configure Settings ===\n")

result = requests.put(
    f"{BASE_URL}/v1/merchants/{MERCHANT_ID}/settings",
    headers=HEADERS,
    json={
        "discountMode": "highest",  # or "stack" to sum all qualifying discounts
        "discountCap": 25,  # max 25% total discount
        "usdcPayment": {
            "enabled": True,
            "evmAddress": MERCHANT_EVM_ADDRESS,
            "preferredChainId": 8453,  # Base
        },
    },
).json()

if result["ok"]:
    data = result["data"]
    print(f"  Discount mode: {data['discountMode']}")
    print(f"  Discount cap:  {data['discountCap']}%")
    print(f"  USDC payments: {'enabled' if data['usdcPayment']['enabled'] else 'disabled'}")
else:
    print(f"  Error: {result['error']['message']}")


# ── Step 5: Publish to directory ─────────────────────────────────

print("\n=== Step 5: Publish to Public Directory ===\n")

result = requests.post(
    f"{BASE_URL}/v1/merchants/{MERCHANT_ID}/directory",
    headers=HEADERS,
).json()

if result["ok"]:
    data = result["data"]
    print(f"  Published: {data['published']}")
    print(f"  Tokens listed:  {data['tokensListed']}")
    print(f"  NFTs listed:    {data['nftCollectionsListed']}")
    print(f"  Discoverable at: GET /v1/merchants?token=UNI")
else:
    print(f"  Error: {result['error']['message']}")


# ── Step 6: Check full status ────────────────────────────────────

print("\n=== Step 6: Full Merchant Status (Owner Only) ===\n")

result = requests.get(
    f"{BASE_URL}/v1/merchants/{MERCHANT_ID}/status",
    headers=HEADERS,
).json()

if result["ok"]:
    data = result["data"]
    print(f"  Name:           {data['companyName']}")
    print(f"  ID:             {data['id']}")
    print(f"  Owner credits:  {data['credits']}")
    print(f"  Discount mode:  {data['discountMode']}")
    print(f"  Discount cap:   {data.get('discountCap', 'none')}%")
    print(f"  In directory:   {data['listedInDirectory']}")
    print(f"  API access:     {data['apiAccessEnabled']}")

    own = data.get("ownToken")
    if own:
        print(f"  Own token:      {own['symbol']} ({len(own.get('tiers', []))} tiers)")

    partners = data.get("partnerTokens", [])
    if partners:
        print(f"  Partner tokens: {len(partners)}")

    nfts = data.get("nftCollections", [])
    if nfts:
        print(f"  NFT collections: {len(nfts)}")

    usdc = data.get("usdcPayment")
    if usdc and usdc.get("enabled"):
        print(f"  USDC wallet:    {usdc['evmAddress'][:10]}...")

    verification = data.get("verification", {})
    print(f"  Domain status:  {verification.get('status', 'unverified')}")
else:
    print(f"  Error: {result['error']['message']}")


print("\n\nMerchant is fully onboarded and discoverable by AI agents.")
print("Next: agents can call GET /v1/discount/check or POST /v1/acp/discount")
print(f"with merchantId='{MERCHANT_ID}' to verify buyers and issue discounts.")
