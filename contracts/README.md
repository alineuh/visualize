# Fractional Art Marketplace (Tezos) — Smart Contracts (SmartPy + Taqueria)

Smart contracts for a fractional art marketplace on Tezos:
- Artists create collections with a `capShare%`
- Artists escrow an existing FA2 NFT (the artwork) to create a sale
- Buyers fund the piece in tez (capped per buyer) and receive transferable FA2 share tokens
- The sale closes when the piece is fully funded

No frontend in this repo. Contracts only.

---

## Tech Stack

- **Tezos**: target chain (local sandbox)
- **Taqueria**: compile / sandbox / deploy / call
- **SmartPy**: contract development
- **FA2 (TZIP-12)**:
  - External FA2 NFT contract for the underlying artwork
  - Internal FA2-like fungible token (`ShareFA2`) for fractional shares
- **Docker**: required for local sandbox

---

## Contracts

### 1) `ShareFA2` (Fungible shares)
Purpose: represent fractional ownership as transferable tokens.

Key behavior:
- One funded artwork sale corresponds to one `token_id` in `ShareFA2`.
- Minting is restricted to `admin` (the Market contract).
- `set_admin` is used during deployment to give the Market minting rights.

Entrypoints:
- `mint(to_, token_id, amount)` (admin only)
- `transfer(...)`
- `update_operators(...)`
- `set_admin(new_admin)` (admin only)

### 2) `FractionalArtMarketV1_FA2` (Funding + NFT escrow + share minting)
Purpose: escrow an FA2 NFT (artwork), accept tez contributions, enforce capShare%, mint shares.

Entrypoints:
- `create_collection(cap_percent)`
- `create_piece_from_nft(collection_id, nft_fa2, nft_token_id, price)`
  - transfers NFT (amount=1) from artist → Market escrow
  - requires the artist set the Market as operator in the NFT FA2 contract
  - allocates a new `share_token_id`
- `buy_piece(piece_id)` payable
  - enforces per-buyer cap and prevents overfunding
  - mints shares to buyer (1:1 with contributed mutez)
  - closes sale at 100% funding
  - v1 behavior: forwards tez immediately to artist

Views:
- `get_collection(collection_id)`
- `get_piece(piece_id)`
- `get_user_contribution(piece_id, user)`
- `get_cap_amount(piece_id)`

---

## v1 Rules (Spec)

- A collection has a `cap_percent` in `[1..100]`.
- For each piece:
  - `max_per_buyer = price * cap_percent / 100`
  - a buyer’s total contributions to that piece cannot exceed `max_per_buyer`
  - the piece cannot be funded above `price`
  - the piece is closed when `total_raised == price`
- Fractionalization is “as fine as needed” based on `cap_percent`:
  - e.g. `cap=20%` implies at least 5 distinct buyers to reach 100% funding

Shares:
- Shares are minted as FA2 fungible balances:
  - `shares_minted = mutez_to_nat(contribution_amount)`
  - (1 tez = 1,000,000 share units)
- Shares do not “inflate”; their market value can change in later versions via secondary trading.

---

## Run (Local)

### 0) Sandbox image (Apple Silicon note)
If you’re on ARM (M1/M2/M3), set a multi-arch Flextesa image before starting the sandbox:
```bash
export TAQ_FLEXTESA_IMAGE=oxheadalpha/flextesa:latest
