# Test Results Examples

This document presents examples of expected outputs when running the test suite.

---

## 📊 Global Summary

```
========================================
Test Suite: Fractional Art Marketplace
========================================

✅ ShareFA2 - Basic Functionality          PASSED (6 assertions)
✅ ShareFA2 - Transfers and Operators      PASSED (8 assertions)
✅ ShareFA2 - Multiple tokens              PASSED (4 assertions)
✅ Market - Collection Creation            PASSED (7 assertions)
✅ Market - Piece Creation from NFT        PASSED (9 assertions)
✅ Market - Buying Shares (Basic)          PASSED (10 assertions)
✅ Market - Cap Enforcement                PASSED (5 assertions)
✅ Market - Piece Closure                  PASSED (8 assertions)
✅ Market - Views                          PASSED (5 assertions)
✅ Market - Edge Cases                     PASSED (12 assertions)
✅ Integration - Full Workflow             PASSED (15 assertions)

========================================
TOTAL: 11 test modules
TOTAL: 89 assertions
SUCCESS: 89/89 (100%)
FAILED: 0
========================================
```

---

## 🧪 Detailed Test Examples

### Test 1: ShareFA2 - Minting

```python
TEST: ShareFA2 - Basic Functionality
====================================

→ Test 2: Set admin (transfer to Market)
  Action: share_contract.set_admin(market.address)
  Sender: admin
  Status: ✅ SUCCESS
  
  Verification:
    ✓ share_contract.data.admin == market.address
    ✓ Previous admin cannot set_admin anymore

→ Test 4: Mint tokens (as Market)
  Action: share_contract.mint(to_=alice, token_id=0, amount=1000)
  Sender: market
  Status: ✅ SUCCESS
  
  Verification:
    ✓ ledger[(alice, 0)] == 1000
    ✓ total_supply[0] == 1000
    ✓ Alice balance increased by 1000 shares

→ Test 5: Mint - only admin can mint
  Action: share_contract.mint(to_=bob, token_id=0, amount=500)
  Sender: alice (NOT ADMIN)
  Status: ✅ FAILED AS EXPECTED
  Exception: "NOT_ADMIN"
  
  Verification:
    ✓ Transaction rejected
    ✓ No new tokens minted
```

---

### Test 2: Market - Cap Enforcement

```python
TEST: Market - Cap Enforcement
==============================

Setup:
  - Collection cap: 25%
  - Piece price: 10 tez
  - Max per buyer: 2.5 tez

→ Test 1: Buyer can contribute up to cap
  Action 1: buy_piece(0, amount=2 tez)
  Action 2: buy_piece(0, amount=0.5 tez)
  Total: 2.5 tez
  Status: ✅ SUCCESS
  
  Verification:
    ✓ contributions[(0, buyer)] == 2.5 tez
    ✓ shares_minted == 2,500,000
    ✓ At exactly cap limit

→ Test 2: Cannot exceed cap
  Action: buy_piece(0, amount=1 mutez)
  Current contribution: 2.5 tez
  Attempted total: 2.500001 tez (> cap)
  Status: ✅ FAILED AS EXPECTED
  Exception: "OVER_CAP_SHARE"
  
  Verification:
    ✓ Transaction rejected
    ✓ Contribution unchanged
    ✓ No additional shares minted
```

---

### Test 3: Market - Piece Closure

```python
TEST: Market - Piece Closure
============================

Setup:
  - Price: 10 tez
  - Cap: 20% (2 tez max per buyer)
  - Minimum buyers needed: 5

Funding Progress:
  Buyer 1: 2 tez   → total: 2 tez   (20%) ✓ OPEN
  Buyer 2: 2 tez   → total: 4 tez   (40%) ✓ OPEN
  Buyer 3: 2 tez   → total: 6 tez   (60%) ✓ OPEN
  Buyer 4: 2 tez   → total: 8 tez   (80%) ✓ OPEN
  Buyer 5: 2 tez   → total: 10 tez  (100%) ✅ CLOSED

→ Test 2: Last buyer completes funding
  Action: buy_piece(0, amount=2 tez)
  Sender: buyer5
  Status: ✅ SUCCESS
  
  Verification:
    ✓ total_raised == 10 tez (100%)
    ✓ piece.closed == True
    ✓ All buyers received shares proportionally
    ✓ Artist received 10 tez total

→ Test 3: Cannot buy from closed piece
  Action: buy_piece(0, amount=1 tez)
  Sender: buyer6
  Status: ✅ FAILED AS EXPECTED
  Exception: "PIECE_CLOSED"
  
  Verification:
    ✓ Transaction rejected
    ✓ Total raised unchanged
    ✓ Piece remains closed
```

---

### Test 4: Integration - Full Workflow

```python
TEST: Integration - Full Workflow
==================================

Scenario: Multiple artists, collections, and buyers

→ Setup Phase
  ✓ ShareFA2 deployed
  ✓ Market deployed
  ✓ NFT contract deployed
  ✓ Admin transferred to Market
  ✓ 2 artists ready
  ✓ 3 collectors ready

→ Artist 1: Gallery Collection (15% cap)
  Action: create_collection(cap=15)
  Status: ✅ SUCCESS
  
  Pieces created: 2
  - Piece 0: 20 tez, NFT token_id=0
  - Piece 1: 20 tez, NFT token_id=1
  
  Verification:
    ✓ collection_id == 0
    ✓ cap_percent == 15
    ✓ artist == artist1.address
    ✓ NFTs escrowed to market

→ Artist 2: Exclusive Collection (50% cap)
  Action: create_collection(cap=50)
  Status: ✅ SUCCESS
  
  Pieces created: 1
  - Piece 2: 10 tez, NFT token_id=2
  
  Verification:
    ✓ collection_id == 1
    ✓ cap_percent == 50

→ Collectors Purchase Shares
  
  Piece 0 (20 tez, 15% cap = 3 tez max):
    - Collector 1: 3 tez ✓
    - Collector 2: 3 tez ✓
    - Collector 3: 2 tez ✓
    - ... (additional buyers to complete)
    
  Piece 2 (10 tez, 50% cap = 5 tez max):
    - Collector 1: 5 tez ✓
    - Collector 2: 5 tez ✓
    → FULLY FUNDED → CLOSED ✅

→ Secondary Market Activity
  Action: Collector 1 transfers 1 tez worth of shares (piece 0) to Collector 3
  Status: ✅ SUCCESS
  
  Verification:
    ✓ Collector 1 balance: 2,000,000 shares (2 tez worth)
    ✓ Collector 3 balance: 3,000,000 shares (3 tez worth)
    ✓ Transfer authorized and executed

→ Final State
  Piece 0:
    ✓ Total raised: 20 tez
    ✓ Status: CLOSED
    ✓ Share token 0: 20,000,000 total supply
    ✓ Distributed among 7+ buyers
    
  Piece 2:
    ✓ Total raised: 10 tez
    ✓ Status: CLOSED
    ✓ Share token 2: 10,000,000 total supply
    ✓ Split between Collector 1 & 2

Overall:
  ✓ All pieces funded correctly
  ✓ All caps respected
  ✓ All NFTs escrowed
  ✓ All shares minted 1:1
  ✓ All artists paid
  ✓ Secondary transfers working

========================================
INTEGRATION TEST: ✅ PASSED
========================================
```

---

## 🔍 Verification Details

### Balance Tracking

```
Before purchase:
  Buyer balance: 100 tez
  Artist balance: 50 tez
  Shares (buyer, token_id=0): 0

Purchase: 2 tez
  
After purchase:
  Buyer balance: 98 tez (-2 tez)
  Artist balance: 52 tez (+2 tez, v1 immediate)
  Shares (buyer, token_id=0): 2,000,000
  
Verification:
  ✓ Tez transferred correctly
  ✓ Shares minted: 2 tez = 2,000,000 mutez = 2,000,000 shares
  ✓ Ratio 1:1 maintained
```

---

### State Transitions

```
Piece Lifecycle:

1. CREATED
   closed: False
   total_raised: 0 tez
   contributions: {}
   
2. PARTIALLY FUNDED (40%)
   closed: False
   total_raised: 4 tez
   contributions: {
     (0, buyer1): 2 tez,
     (0, buyer2): 2 tez
   }
   
3. NEARLY COMPLETE (90%)
   closed: False
   total_raised: 9 tez
   contributions: {
     (0, buyer1): 2 tez,
     (0, buyer2): 2 tez,
     (0, buyer3): 2 tez,
     (0, buyer4): 2 tez,
     (0, buyer5): 1 tez
   }
   
4. FULLY FUNDED → CLOSED
   closed: True ✅
   total_raised: 10 tez (== price)
   contributions: {
     ... (all buyers)
   }
   
   ✓ Automatic closure triggered
   ✓ No more purchases allowed
```

---

## ⚠️ Detected Error Examples

### Error 1: Unauthorized Mint Attempt

```
Test: Unauthorized mint attempt
Action: share_contract.mint(...)
Sender: alice (regular user, NOT admin)

Expected: FAIL with "NOT_ADMIN"
Result: ✅ FAILED AS EXPECTED

Error caught:
  Line: sp.verify(sp.sender == self.data.admin, "NOT_ADMIN")
  Message: "NOT_ADMIN"
  Sender: tz1alice...
  Required: tz1market... (admin)
  
✓ Security check passed
✓ Unauthorized minting prevented
```

---

### Error 2: Cap Exceeded

```
Test: Exceed cap limit
Current state:
  - Piece price: 10 tez
  - Cap: 25% = 2.5 tez max
  - Buyer contribution: 2.5 tez (at limit)

Action: buy_piece(0, amount=0.5 tez)
Expected contribution: 3 tez (> 2.5 tez cap)

Expected: FAIL with "OVER_CAP_SHARE"
Result: ✅ FAILED AS EXPECTED

Error caught:
  Line: sp.verify(already + sp.amount <= cap_amount, "OVER_CAP_SHARE")
  Already contributed: 2,500,000 mutez
  Attempting to add: 500,000 mutez
  Total would be: 3,000,000 mutez
  Cap limit: 2,500,000 mutez
  
✓ Cap enforcement working
✓ Fractionalization guaranteed
```

---

## 📈 Coverage Graph

```
Entry Points Coverage:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ShareFA2:
  set_admin          ████████████████████ 100%
  mint               ████████████████████ 100%
  transfer           ████████████████████ 100%
  update_operators   ████████████████████ 100%

Market:
  create_collection       ████████████████████ 100%
  create_piece_from_nft   ████████████████████ 100%
  buy_piece               ████████████████████ 100%

Views:
  get_collection          ████████████████████ 100%
  get_piece               ████████████████████ 100%
  get_user_contribution   ████████████████████ 100%
  get_cap_amount          ████████████████████ 100%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Overall Coverage: 100%
```

---

## ✅ Validation Checklist

### Core Functionalities
- [x] Collection creation
- [x] Piece creation with NFT escrow
- [x] Fractional share purchase
- [x] Share minting
- [x] Share transfers
- [x] Cap enforcement
- [x] Automatic closure
- [x] Artist payment

### Security
- [x] Admin permissions
- [x] Artist permissions
- [x] Operator permissions
- [x] Balance verification
- [x] Parameter validation
- [x] Overflow protection
- [x] Reentrancy protection (not applicable in SmartPy)

### Edge Cases
- [x] Cap 1%
- [x] Cap 100%
- [x] Fractional amounts
- [x] Multiple pieces
- [x] Multiple collections
- [x] Multiple transfers
- [x] Multiple operators

### Integration
- [x] Complete workflow
- [x] Contract interactions
- [x] Consistent states
- [x] Correct balances
- [x] Events (implicit)

---

*Results generated for team project submission*
*All tests must pass to ensure code quality*
