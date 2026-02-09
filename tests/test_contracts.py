"""
Comprehensive test suite for Fractional Art Marketplace
Tests both ShareFA2 and FractionalArtMarketV1_FA2 contracts
"""

import smartpy as sp


import sys
sys.path.append('..') 
from contracts.share_fa2 import ShareFA2
from contracts.market_v1_fa2 import FractionalArtMarketV1_FA2


class MockNFT_FA2(sp.Contract):
    """
    Minimal FA2 NFT contract for testing.
    Allows minting and transferring NFTs.
    """
    def __init__(self):
        self.init(
            ledger=sp.big_map(
                tkey=sp.TPair(sp.TAddress, sp.TNat),
                tvalue=sp.TNat
            ),
            operators=sp.big_map(
                tkey=sp.TRecord(
                    owner=sp.TAddress,
                    operator=sp.TAddress,
                    token_id=sp.TNat
                ).layout(("owner", ("operator", "token_id"))),
                tvalue=sp.TUnit
            )
        )

    @sp.entry_point
    def mint(self, params):
        """Mint an NFT to an address"""
        sp.set_type(params, sp.TRecord(
            to_=sp.TAddress,
            token_id=sp.TNat
        ).layout(("to_", "token_id")))
        
        key = sp.pair(params.to_, params.token_id)
        self.data.ledger[key] = 1

    @sp.entry_point
    def update_operators(self, params):
        """Standard FA2 update_operators"""
        t_op = sp.TRecord(
            owner=sp.TAddress,
            operator=sp.TAddress,
            token_id=sp.TNat
        ).layout(("owner", ("operator", "token_id")))
        
        t_item = sp.TVariant(
            add_operator=t_op,
            remove_operator=t_op
        )
        
        sp.set_type(params, sp.TList(t_item))
        
        sp.for item in params:
            sp.if item.is_variant("add_operator"):
                r = item.open_variant("add_operator")
                sp.verify(sp.sender == r.owner, "NOT_OWNER")
                key = sp.record(
                    owner=r.owner,
                    operator=r.operator,
                    token_id=r.token_id
                )
                self.data.operators[key] = sp.unit
            sp.else:
                r = item.open_variant("remove_operator")
                sp.verify(sp.sender == r.owner, "NOT_OWNER")
                key = sp.record(
                    owner=r.owner,
                    operator=r.operator,
                    token_id=r.token_id
                )
                sp.if self.data.operators.contains(key):
                    del self.data.operators[key]

    @sp.entry_point
    def transfer(self, txs):
        """Standard FA2 transfer"""
        t_tx = sp.TRecord(
            to_=sp.TAddress,
            token_id=sp.TNat,
            amount=sp.TNat
        ).layout(("to_", ("token_id", "amount")))
        
        t_item = sp.TRecord(
            from_=sp.TAddress,
            txs=sp.TList(t_tx)
        ).layout(("from_", "txs"))
        
        sp.set_type(txs, sp.TList(t_item))
        
        sp.for batch in txs:
            sp.for tx in batch.txs:
                # Check operator or owner
                is_operator = self.data.operators.contains(
                    sp.record(
                        owner=batch.from_,
                        operator=sp.sender,
                        token_id=tx.token_id
                    )
                )
                sp.verify(
                    (sp.sender == batch.from_) | is_operator,
                    "NOT_AUTHORIZED"
                )
                
                # Transfer
                from_key = sp.pair(batch.from_, tx.token_id)
                to_key = sp.pair(tx.to_, tx.token_id)
                
                from_balance = self.data.ledger.get(from_key, 0)
                sp.verify(from_balance >= tx.amount, "INSUFFICIENT_BALANCE")
                
                self.data.ledger[from_key] = sp.as_nat(from_balance - tx.amount)
                self.data.ledger[to_key] = self.data.ledger.get(to_key, 0) + tx.amount


# ============================================================================
# TEST MODULE: ShareFA2
# ============================================================================

@sp.add_test(name="ShareFA2 - Basic Functionality")
def test_share_fa2_basic():
    scenario = sp.test_scenario()
    scenario.h1("ShareFA2 - Basic Functionality Tests")
    
    # Test accounts
    admin = sp.test_account("Admin")
    alice = sp.test_account("Alice")
    bob = sp.test_account("Bob")
    market = sp.test_account("Market")
    
    # Deploy ShareFA2
    share_contract = ShareFA2(admin=admin.address)
    scenario += share_contract
    
    scenario.h2("Test 1: Initial state")
    scenario.verify(share_contract.data.admin == admin.address)
    
    scenario.h2("Test 2: Set admin (transfer to Market)")
    share_contract.set_admin(market.address).run(sender=admin)
    scenario.verify(share_contract.data.admin == market.address)
    
    scenario.h2("Test 3: Set admin - only current admin can call")
    share_contract.set_admin(alice.address).run(
        sender=bob,
        valid=False,
        exception="NOT_ADMIN"
    )
    
    scenario.h2("Test 4: Mint tokens (as Market)")
    share_contract.mint(
        sp.record(to_=alice.address, token_id=0, amount=1000)
    ).run(sender=market)
    
    # Verify balance
    alice_balance = share_contract.data.ledger.get(
        sp.pair(alice.address, 0),
        0
    )
    scenario.verify(alice_balance == 1000)
    scenario.verify(share_contract.data.total_supply[0] == 1000)
    
    scenario.h2("Test 5: Mint - only admin can mint")
    share_contract.mint(
        sp.record(to_=bob.address, token_id=0, amount=500)
    ).run(
        sender=alice,
        valid=False,
        exception="NOT_ADMIN"
    )
    
    scenario.h2("Test 6: Mint - cannot mint zero")
    share_contract.mint(
        sp.record(to_=alice.address, token_id=1, amount=0)
    ).run(
        sender=market,
        valid=False,
        exception="ZERO_MINT"
    )


@sp.add_test(name="ShareFA2 - Transfers and Operators")
def test_share_fa2_transfers():
    scenario = sp.test_scenario()
    scenario.h1("ShareFA2 - Transfers and Operators")
    
    # Test accounts
    admin = sp.test_account("Admin")
    alice = sp.test_account("Alice")
    bob = sp.test_account("Bob")
    operator = sp.test_account("Operator")
    
    # Deploy and setup
    share_contract = ShareFA2(admin=admin.address)
    scenario += share_contract
    
    # Mint tokens to Alice
    share_contract.mint(
        sp.record(to_=alice.address, token_id=0, amount=1000)
    ).run(sender=admin)
    
    scenario.h2("Test 1: Direct transfer (owner)")
    share_contract.transfer([
        sp.record(
            from_=alice.address,
            txs=[
                sp.record(to_=bob.address, token_id=0, amount=300)
            ]
        )
    ]).run(sender=alice)
    
    scenario.verify(
        share_contract.data.ledger[sp.pair(alice.address, 0)] == 700
    )
    scenario.verify(
        share_contract.data.ledger[sp.pair(bob.address, 0)] == 300
    )
    
    scenario.h2("Test 2: Transfer - insufficient balance")
    share_contract.transfer([
        sp.record(
            from_=alice.address,
            txs=[
                sp.record(to_=bob.address, token_id=0, amount=800)
            ]
        )
    ]).run(
        sender=alice,
        valid=False,
        exception="INSUFFICIENT_BALANCE"
    )
    
    scenario.h2("Test 3: Transfer - unauthorized (not owner or operator)")
    share_contract.transfer([
        sp.record(
            from_=alice.address,
            txs=[
                sp.record(to_=bob.address, token_id=0, amount=100)
            ]
        )
    ]).run(
        sender=bob,
        valid=False,
        exception="NOT_OPERATOR"
    )
    
    scenario.h2("Test 4: Add operator")
    share_contract.update_operators([
        sp.variant("add_operator", sp.record(
            owner=alice.address,
            operator=operator.address,
            token_id=0
        ))
    ]).run(sender=alice)
    
    # Verify operator is added
    op_key = sp.record(
        owner=alice.address,
        operator=operator.address,
        token_id=0
    )
    scenario.verify(share_contract.data.operators.contains(op_key))
    
    scenario.h2("Test 5: Transfer via operator")
    share_contract.transfer([
        sp.record(
            from_=alice.address,
            txs=[
                sp.record(to_=bob.address, token_id=0, amount=200)
            ]
        )
    ]).run(sender=operator)
    
    scenario.verify(
        share_contract.data.ledger[sp.pair(alice.address, 0)] == 500
    )
    scenario.verify(
        share_contract.data.ledger[sp.pair(bob.address, 0)] == 500
    )
    
    scenario.h2("Test 6: Remove operator")
    share_contract.update_operators([
        sp.variant("remove_operator", sp.record(
            owner=alice.address,
            operator=operator.address,
            token_id=0
        ))
    ]).run(sender=alice)
    
    scenario.verify(~share_contract.data.operators.contains(op_key))
    
    scenario.h2("Test 7: Cannot transfer after operator removed")
    share_contract.transfer([
        sp.record(
            from_=alice.address,
            txs=[
                sp.record(to_=bob.address, token_id=0, amount=100)
            ]
        )
    ]).run(
        sender=operator,
        valid=False,
        exception="NOT_OPERATOR"
    )
    
    scenario.h2("Test 8: Update operators - only owner can add/remove")
    share_contract.update_operators([
        sp.variant("add_operator", sp.record(
            owner=alice.address,
            operator=operator.address,
            token_id=0
        ))
    ]).run(
        sender=bob,
        valid=False,
        exception="NOT_OWNER"
    )


@sp.add_test(name="ShareFA2 - Multiple tokens and batched transfers")
def test_share_fa2_multi_token():
    scenario = sp.test_scenario()
    scenario.h1("ShareFA2 - Multiple Tokens and Batched Transfers")
    
    admin = sp.test_account("Admin")
    alice = sp.test_account("Alice")
    bob = sp.test_account("Bob")
    
    share_contract = ShareFA2(admin=admin.address)
    scenario += share_contract
    
    scenario.h2("Test 1: Mint multiple token IDs")
    share_contract.mint(
        sp.record(to_=alice.address, token_id=0, amount=1000)
    ).run(sender=admin)
    
    share_contract.mint(
        sp.record(to_=alice.address, token_id=1, amount=2000)
    ).run(sender=admin)
    
    share_contract.mint(
        sp.record(to_=alice.address, token_id=2, amount=500)
    ).run(sender=admin)
    
    scenario.verify(share_contract.data.total_supply[0] == 1000)
    scenario.verify(share_contract.data.total_supply[1] == 2000)
    scenario.verify(share_contract.data.total_supply[2] == 500)
    
    scenario.h2("Test 2: Batched transfer (multiple token IDs)")
    share_contract.transfer([
        sp.record(
            from_=alice.address,
            txs=[
                sp.record(to_=bob.address, token_id=0, amount=100),
                sp.record(to_=bob.address, token_id=1, amount=200),
                sp.record(to_=bob.address, token_id=2, amount=50)
            ]
        )
    ]).run(sender=alice)
    
    scenario.verify(
        share_contract.data.ledger[sp.pair(bob.address, 0)] == 100
    )
    scenario.verify(
        share_contract.data.ledger[sp.pair(bob.address, 1)] == 200
    )
    scenario.verify(
        share_contract.data.ledger[sp.pair(bob.address, 2)] == 50
    )


# ============================================================================
# TEST MODULE: FractionalArtMarketV1_FA2
# ============================================================================

@sp.add_test(name="Market - Collection Creation")
def test_market_collections():
    scenario = sp.test_scenario()
    scenario.h1("Market - Collection Creation")
    
    artist = sp.test_account("Artist")
    admin = sp.test_account("Admin")
    
    # Deploy contracts
    share_contract = ShareFA2(admin=admin.address)
    scenario += share_contract
    
    market = FractionalArtMarketV1_FA2(share_fa2=share_contract.address)
    scenario += market
    
    # Transfer admin rights to market
    share_contract.set_admin(market.address).run(sender=admin)
    
    scenario.h2("Test 1: Create collection with valid cap")
    market.create_collection(20).run(sender=artist)
    
    scenario.verify(market.data.next_collection_id == 1)
    scenario.verify(market.data.collections[0].artist == artist.address)
    scenario.verify(market.data.collections[0].cap_percent == 20)
    
    scenario.h2("Test 2: Create multiple collections")
    market.create_collection(50).run(sender=artist)
    market.create_collection(10).run(sender=artist)
    
    scenario.verify(market.data.next_collection_id == 3)
    scenario.verify(market.data.collections[1].cap_percent == 50)
    scenario.verify(market.data.collections[2].cap_percent == 10)
    
    scenario.h2("Test 3: Cap too low (0%)")
    market.create_collection(0).run(
        sender=artist,
        valid=False,
        exception="CAP_TOO_LOW"
    )
    
    scenario.h2("Test 4: Cap too high (>100%)")
    market.create_collection(101).run(
        sender=artist,
        valid=False,
        exception="CAP_TOO_HIGH"
    )
    
    scenario.h2("Test 5: Edge case - cap at 1%")
    market.create_collection(1).run(sender=artist)
    scenario.verify(market.data.collections[3].cap_percent == 1)
    
    scenario.h2("Test 6: Edge case - cap at 100%")
    market.create_collection(100).run(sender=artist)
    scenario.verify(market.data.collections[4].cap_percent == 100)


@sp.add_test(name="Market - Piece Creation from NFT")
def test_market_piece_creation():
    scenario = sp.test_scenario()
    scenario.h1("Market - Piece Creation from NFT")
    
    artist = sp.test_account("Artist")
    admin = sp.test_account("Admin")
    other = sp.test_account("Other")
    
    # Deploy contracts
    share_contract = ShareFA2(admin=admin.address)
    scenario += share_contract
    
    market = FractionalArtMarketV1_FA2(share_fa2=share_contract.address)
    scenario += market
    
    nft_contract = MockNFT_FA2()
    scenario += nft_contract
    
    # Setup: transfer admin to market
    share_contract.set_admin(market.address).run(sender=admin)
    
    # Mint NFT to artist
    nft_contract.mint(
        sp.record(to_=artist.address, token_id=0)
    ).run(sender=artist)
    
    # Create collection
    market.create_collection(20).run(sender=artist)
    
    scenario.h2("Test 1: Artist approves market as operator")
    nft_contract.update_operators([
        sp.variant("add_operator", sp.record(
            owner=artist.address,
            operator=market.address,
            token_id=0
        ))
    ]).run(sender=artist)
    
    scenario.h2("Test 2: Create piece from NFT")
    market.create_piece_from_nft(
        sp.record(
            collection_id=0,
            nft_fa2=nft_contract.address,
            nft_token_id=0,
            price=sp.tez(10)
        )
    ).run(sender=artist)
    
    # Verify piece created
    scenario.verify(market.data.next_piece_id == 1)
    scenario.verify(market.data.pieces[0].collection_id == 0)
    scenario.verify(market.data.pieces[0].price == sp.tez(10))
    scenario.verify(market.data.pieces[0].total_raised == sp.tez(0))
    scenario.verify(market.data.pieces[0].closed == False)
    scenario.verify(market.data.pieces[0].nft_fa2 == nft_contract.address)
    scenario.verify(market.data.pieces[0].nft_token_id == 0)
    scenario.verify(market.data.pieces[0].share_token_id == 0)
    
    # Verify NFT transferred to market
    scenario.verify(
        nft_contract.data.ledger[sp.pair(market.address, 0)] == 1
    )
    scenario.verify(
        nft_contract.data.ledger.get(sp.pair(artist.address, 0), 0) == 0
    )
    
    scenario.h2("Test 3: Cannot create piece without being artist")
    nft_contract.mint(
        sp.record(to_=artist.address, token_id=1)
    ).run(sender=artist)
    
    nft_contract.update_operators([
        sp.variant("add_operator", sp.record(
            owner=artist.address,
            operator=market.address,
            token_id=1
        ))
    ]).run(sender=artist)
    
    market.create_piece_from_nft(
        sp.record(
            collection_id=0,
            nft_fa2=nft_contract.address,
            nft_token_id=1,
            price=sp.tez(5)
        )
    ).run(
        sender=other,
        valid=False,
        exception="NOT_ARTIST"
    )
    
    scenario.h2("Test 4: Cannot create piece with non-existent collection")
    market.create_piece_from_nft(
        sp.record(
            collection_id=999,
            nft_fa2=nft_contract.address,
            nft_token_id=1,
            price=sp.tez(5)
        )
    ).run(
        sender=artist,
        valid=False,
        exception="NO_COLLECTION"
    )
    
    scenario.h2("Test 5: Cannot create piece with zero price")
    market.create_piece_from_nft(
        sp.record(
            collection_id=0,
            nft_fa2=nft_contract.address,
            nft_token_id=1,
            price=sp.mutez(0)
        )
    ).run(
        sender=artist,
        valid=False,
        exception="BAD_PRICE"
    )


@sp.add_test(name="Market - Buying Shares (Basic)")
def test_market_buying_basic():
    scenario = sp.test_scenario()
    scenario.h1("Market - Buying Shares (Basic)")
    
    artist = sp.test_account("Artist")
    buyer1 = sp.test_account("Buyer1")
    buyer2 = sp.test_account("Buyer2")
    admin = sp.test_account("Admin")
    
    # Deploy contracts
    share_contract = ShareFA2(admin=admin.address)
    scenario += share_contract
    
    market = FractionalArtMarketV1_FA2(share_fa2=share_contract.address)
    scenario += market
    
    nft_contract = MockNFT_FA2()
    scenario += nft_contract
    
    # Setup
    share_contract.set_admin(market.address).run(sender=admin)
    
    # Mint NFT and approve
    nft_contract.mint(sp.record(to_=artist.address, token_id=0)).run(sender=artist)
    nft_contract.update_operators([
        sp.variant("add_operator", sp.record(
            owner=artist.address,
            operator=market.address,
            token_id=0
        ))
    ]).run(sender=artist)
    
    # Create collection (20% cap) and piece (10 tez)
    market.create_collection(20).run(sender=artist)
    market.create_piece_from_nft(
        sp.record(
            collection_id=0,
            nft_fa2=nft_contract.address,
            nft_token_id=0,
            price=sp.tez(10)
        )
    ).run(sender=artist)
    
    scenario.h2("Test 1: Buyer purchases shares")
    artist_balance_before = scenario.compute(artist.balance)
    
    market.buy_piece(0).run(
        sender=buyer1,
        amount=sp.tez(2)
    )
    
    # Verify contribution recorded
    scenario.verify(
        market.data.contributions[sp.pair(0, buyer1.address)] == sp.tez(2)
    )
    
    # Verify total raised
    scenario.verify(market.data.pieces[0].total_raised == sp.tez(2))
    
    # Verify shares minted (2 tez = 2_000_000 mutez = 2_000_000 shares)
    scenario.verify(
        share_contract.data.ledger[sp.pair(buyer1.address, 0)] == 2_000_000
    )
    
    # Verify artist received payment (v1 immediate payment)
    scenario.verify(artist.balance == artist_balance_before + sp.tez(2))
    
    scenario.h2("Test 2: Second buyer purchases shares")
    market.buy_piece(0).run(
        sender=buyer2,
        amount=sp.tez(1)
    )
    
    scenario.verify(
        market.data.contributions[sp.pair(0, buyer2.address)] == sp.tez(1)
    )
    scenario.verify(market.data.pieces[0].total_raised == sp.tez(3))
    scenario.verify(
        share_contract.data.ledger[sp.pair(buyer2.address, 0)] == 1_000_000
    )
    
    scenario.h2("Test 3: Buyer adds more to their contribution")
    market.buy_piece(0).run(
        sender=buyer1,
        amount=sp.mutez(500_000)
    )
    
    scenario.verify(
        market.data.contributions[sp.pair(0, buyer1.address)] == sp.mutez(2_500_000)
    )
    scenario.verify(
        share_contract.data.ledger[sp.pair(buyer1.address, 0)] == 2_500_000
    )
    
    scenario.h2("Test 4: Cannot buy with zero amount")
    market.buy_piece(0).run(
        sender=buyer1,
        amount=sp.mutez(0),
        valid=False,
        exception="SEND_TEZ"
    )
    
    scenario.h2("Test 5: Cannot buy non-existent piece")
    market.buy_piece(999).run(
        sender=buyer1,
        amount=sp.tez(1),
        valid=False,
        exception="NO_PIECE"
    )


@sp.add_test(name="Market - Cap Enforcement")
def test_market_cap_enforcement():
    scenario = sp.test_scenario()
    scenario.h1("Market - Cap Enforcement")
    
    artist = sp.test_account("Artist")
    buyer = sp.test_account("Buyer")
    admin = sp.test_account("Admin")
    
    # Deploy contracts
    share_contract = ShareFA2(admin=admin.address)
    scenario += share_contract
    
    market = FractionalArtMarketV1_FA2(share_fa2=share_contract.address)
    scenario += market
    
    nft_contract = MockNFT_FA2()
    scenario += nft_contract
    
    # Setup
    share_contract.set_admin(market.address).run(sender=admin)
    nft_contract.mint(sp.record(to_=artist.address, token_id=0)).run(sender=artist)
    nft_contract.update_operators([
        sp.variant("add_operator", sp.record(
            owner=artist.address,
            operator=market.address,
            token_id=0
        ))
    ]).run(sender=artist)
    
    # Create collection with 25% cap and piece at 10 tez
    # Max per buyer = 10 * 25 / 100 = 2.5 tez
    market.create_collection(25).run(sender=artist)
    market.create_piece_from_nft(
        sp.record(
            collection_id=0,
            nft_fa2=nft_contract.address,
            nft_token_id=0,
            price=sp.tez(10)
        )
    ).run(sender=artist)
    
    scenario.h2("Test 1: Buyer can contribute up to cap")
    market.buy_piece(0).run(
        sender=buyer,
        amount=sp.tez(2)
    )
    
    market.buy_piece(0).run(
        sender=buyer,
        amount=sp.mutez(500_000)  # 0.5 tez more = 2.5 total
    )
    
    scenario.verify(
        market.data.contributions[sp.pair(0, buyer.address)] == sp.mutez(2_500_000)
    )
    
    scenario.h2("Test 2: Cannot exceed cap")
    market.buy_piece(0).run(
        sender=buyer,
        amount=sp.mutez(1),
        valid=False,
        exception="OVER_CAP_SHARE"
    )
    
    scenario.h2("Test 3: Cannot exceed cap in single purchase")
    buyer2 = sp.test_account("Buyer2")
    
    market.buy_piece(0).run(
        sender=buyer2,
        amount=sp.tez(3),  # Exceeds 2.5 tez cap
        valid=False,
        exception="OVER_CAP_SHARE"
    )


@sp.add_test(name="Market - Piece Closure")
def test_market_piece_closure():
    scenario = sp.test_scenario()
    scenario.h1("Market - Piece Closure")
    
    artist = sp.test_account("Artist")
    buyer1 = sp.test_account("Buyer1")
    buyer2 = sp.test_account("Buyer2")
    buyer3 = sp.test_account("Buyer3")
    buyer4 = sp.test_account("Buyer4")
    buyer5 = sp.test_account("Buyer5")
    admin = sp.test_account("Admin")
    
    # Deploy contracts
    share_contract = ShareFA2(admin=admin.address)
    scenario += share_contract
    
    market = FractionalArtMarketV1_FA2(share_fa2=share_contract.address)
    scenario += market
    
    nft_contract = MockNFT_FA2()
    scenario += nft_contract
    
    # Setup
    share_contract.set_admin(market.address).run(sender=admin)
    nft_contract.mint(sp.record(to_=artist.address, token_id=0)).run(sender=artist)
    nft_contract.update_operators([
        sp.variant("add_operator", sp.record(
            owner=artist.address,
            operator=market.address,
            token_id=0
        ))
    ]).run(sender=artist)
    
    # Create collection with 20% cap and piece at 10 tez
    # Max per buyer = 2 tez, needs at least 5 buyers
    market.create_collection(20).run(sender=artist)
    market.create_piece_from_nft(
        sp.record(
            collection_id=0,
            nft_fa2=nft_contract.address,
            nft_token_id=0,
            price=sp.tez(10)
        )
    ).run(sender=artist)
    
    scenario.h2("Test 1: Multiple buyers fund the piece")
    market.buy_piece(0).run(sender=buyer1, amount=sp.tez(2))
    scenario.verify(market.data.pieces[0].closed == False)
    
    market.buy_piece(0).run(sender=buyer2, amount=sp.tez(2))
    scenario.verify(market.data.pieces[0].closed == False)
    
    market.buy_piece(0).run(sender=buyer3, amount=sp.tez(2))
    scenario.verify(market.data.pieces[0].closed == False)
    
    market.buy_piece(0).run(sender=buyer4, amount=sp.tez(2))
    scenario.verify(market.data.pieces[0].closed == False)
    
    scenario.h2("Test 2: Last buyer completes funding - piece closes")
    market.buy_piece(0).run(sender=buyer5, amount=sp.tez(2))
    
    scenario.verify(market.data.pieces[0].total_raised == sp.tez(10))
    scenario.verify(market.data.pieces[0].closed == True)
    
    scenario.h2("Test 3: Cannot buy from closed piece")
    buyer6 = sp.test_account("Buyer6")
    
    market.buy_piece(0).run(
        sender=buyer6,
        amount=sp.tez(1),
        valid=False,
        exception="PIECE_CLOSED"
    )
    
    scenario.h2("Test 4: Cannot overfund the piece")
    # Create another piece
    nft_contract.mint(sp.record(to_=artist.address, token_id=1)).run(sender=artist)
    nft_contract.update_operators([
        sp.variant("add_operator", sp.record(
            owner=artist.address,
            operator=market.address,
            token_id=1
        ))
    ]).run(sender=artist)
    
    market.create_piece_from_nft(
        sp.record(
            collection_id=0,
            nft_fa2=nft_contract.address,
            nft_token_id=1,
            price=sp.tez(5)
        )
    ).run(sender=artist)
    
    # Try to fund more than the price (even if within cap)
    # Cap = 20% of 5 tez = 1 tez per buyer
    # But let's try funding 3 tez from one buyer (exceeds both cap and total)
    market.buy_piece(1).run(
        sender=buyer1,
        amount=sp.tez(3),
        valid=False,
        exception="OVER_CAP_SHARE"
    )
    
    # Fund partially, then try to overfund total
    market.buy_piece(1).run(sender=buyer1, amount=sp.tez(1))
    market.buy_piece(1).run(sender=buyer2, amount=sp.tez(1))
    market.buy_piece(1).run(sender=buyer3, amount=sp.tez(1))
    market.buy_piece(1).run(sender=buyer4, amount=sp.tez(1))
    market.buy_piece(1).run(sender=buyer5, amount=sp.tez(1))
    
    # Now at 5 tez total, piece should be closed
    scenario.verify(market.data.pieces[1].closed == True)


@sp.add_test(name="Market - Views")
def test_market_views():
    scenario = sp.test_scenario()
    scenario.h1("Market - Views (On-chain)")
    
    artist = sp.test_account("Artist")
    buyer = sp.test_account("Buyer")
    admin = sp.test_account("Admin")
    
    # Deploy contracts
    share_contract = ShareFA2(admin=admin.address)
    scenario += share_contract
    
    market = FractionalArtMarketV1_FA2(share_fa2=share_contract.address)
    scenario += market
    
    nft_contract = MockNFT_FA2()
    scenario += nft_contract
    
    # Setup
    share_contract.set_admin(market.address).run(sender=admin)
    nft_contract.mint(sp.record(to_=artist.address, token_id=0)).run(sender=artist)
    nft_contract.update_operators([
        sp.variant("add_operator", sp.record(
            owner=artist.address,
            operator=market.address,
            token_id=0
        ))
    ]).run(sender=artist)
    
    # Create collection and piece
    market.create_collection(30).run(sender=artist)
    market.create_piece_from_nft(
        sp.record(
            collection_id=0,
            nft_fa2=nft_contract.address,
            nft_token_id=0,
            price=sp.tez(10)
        )
    ).run(sender=artist)
    
    scenario.h2("Test 1: get_collection view")
    result = scenario.compute(market.get_collection(0))
    scenario.verify(result.artist == artist.address)
    scenario.verify(result.cap_percent == 30)
    
    scenario.h2("Test 2: get_piece view")
    result = scenario.compute(market.get_piece(0))
    scenario.verify(result.collection_id == 0)
    scenario.verify(result.price == sp.tez(10))
    scenario.verify(result.total_raised == sp.tez(0))
    scenario.verify(result.closed == False)
    
    scenario.h2("Test 3: get_cap_amount view")
    # Cap = 30% of 10 tez = 3 tez
    cap_amount = scenario.compute(market.get_cap_amount(0))
    scenario.verify(cap_amount == sp.tez(3))
    
    scenario.h2("Test 4: get_user_contribution view (before purchase)")
    contrib = scenario.compute(market.get_user_contribution(
        sp.record(piece_id=0, user=buyer.address)
    ))
    scenario.verify(contrib == sp.tez(0))
    
    scenario.h2("Test 5: get_user_contribution view (after purchase)")
    market.buy_piece(0).run(sender=buyer, amount=sp.tez(2))
    
    contrib = scenario.compute(market.get_user_contribution(
        sp.record(piece_id=0, user=buyer.address)
    ))
    scenario.verify(contrib == sp.tez(2))


@sp.add_test(name="Market - Edge Cases and Complex Scenarios")
def test_market_edge_cases():
    scenario = sp.test_scenario()
    scenario.h1("Market - Edge Cases")
    
    artist = sp.test_account("Artist")
    buyer = sp.test_account("Buyer")
    admin = sp.test_account("Admin")
    
    # Deploy contracts
    share_contract = ShareFA2(admin=admin.address)
    scenario += share_contract
    
    market = FractionalArtMarketV1_FA2(share_fa2=share_contract.address)
    scenario += market
    
    nft_contract = MockNFT_FA2()
    scenario += nft_contract
    
    # Setup
    share_contract.set_admin(market.address).run(sender=admin)
    
    scenario.h2("Test 1: Collection with 100% cap (single buyer can fund)")
    nft_contract.mint(sp.record(to_=artist.address, token_id=0)).run(sender=artist)
    nft_contract.update_operators([
        sp.variant("add_operator", sp.record(
            owner=artist.address,
            operator=market.address,
            token_id=0
        ))
    ]).run(sender=artist)
    
    market.create_collection(100).run(sender=artist)
    market.create_piece_from_nft(
        sp.record(
            collection_id=0,
            nft_fa2=nft_contract.address,
            nft_token_id=0,
            price=sp.tez(5)
        )
    ).run(sender=artist)
    
    # Single buyer funds entire piece
    market.buy_piece(0).run(sender=buyer, amount=sp.tez(5))
    
    scenario.verify(market.data.pieces[0].closed == True)
    scenario.verify(
        share_contract.data.ledger[sp.pair(buyer.address, 0)] == 5_000_000
    )
    
    scenario.h2("Test 2: Collection with 1% cap (requires 100 buyers minimum)")
    nft_contract.mint(sp.record(to_=artist.address, token_id=1)).run(sender=artist)
    nft_contract.update_operators([
        sp.variant("add_operator", sp.record(
            owner=artist.address,
            operator=market.address,
            token_id=1
        ))
    ]).run(sender=artist)
    
    market.create_collection(1).run(sender=artist)
    market.create_piece_from_nft(
        sp.record(
            collection_id=1,
            nft_fa2=nft_contract.address,
            nft_token_id=1,
            price=sp.tez(100)
        )
    ).run(sender=artist)
    
    # Max per buyer = 100 * 1 / 100 = 1 tez
    cap = scenario.compute(market.get_cap_amount(1))
    scenario.verify(cap == sp.tez(1))
    
    # Buyer can only contribute 1 tez
    market.buy_piece(1).run(sender=buyer, amount=sp.tez(1))
    
    market.buy_piece(1).run(
        sender=buyer,
        amount=sp.mutez(1),
        valid=False,
        exception="OVER_CAP_SHARE"
    )
    
    scenario.h2("Test 3: Fractional tez amounts")
    nft_contract.mint(sp.record(to_=artist.address, token_id=2)).run(sender=artist)
    nft_contract.update_operators([
        sp.variant("add_operator", sp.record(
            owner=artist.address,
            operator=market.address,
            token_id=2
        ))
    ]).run(sender=artist)
    
    market.create_collection(33).run(sender=artist)
    market.create_piece_from_nft(
        sp.record(
            collection_id=2,
            nft_fa2=nft_contract.address,
            nft_token_id=2,
            price=sp.mutez(3_333_333)  # ~3.33 tez
        )
    ).run(sender=artist)
    
    # Cap = 3_333_333 * 33 / 100 = 1_099_999
    buyer2 = sp.test_account("Buyer2")
    market.buy_piece(2).run(sender=buyer2, amount=sp.mutez(1_099_999))
    
    scenario.verify(
        market.data.contributions[sp.pair(2, buyer2.address)] == sp.mutez(1_099_999)
    )
    
    scenario.h2("Test 4: Multiple pieces in same collection")
    # Create 3 pieces in same collection
    for i in range(3, 6):
        nft_contract.mint(sp.record(to_=artist.address, token_id=i)).run(sender=artist)
        nft_contract.update_operators([
            sp.variant("add_operator", sp.record(
                owner=artist.address,
                operator=market.address,
                token_id=i
            ))
        ]).run(sender=artist)
        
        market.create_piece_from_nft(
            sp.record(
                collection_id=0,  # Same collection (100% cap)
                nft_fa2=nft_contract.address,
                nft_token_id=i,
                price=sp.tez(2)
            )
        ).run(sender=artist)
    
    # Each piece should have different share_token_id
    scenario.verify(market.data.pieces[3].share_token_id == 3)
    scenario.verify(market.data.pieces[4].share_token_id == 4)
    scenario.verify(market.data.pieces[5].share_token_id == 5)
    
    # Buyer can fully fund each piece separately (100% cap)
    buyer3 = sp.test_account("Buyer3")
    market.buy_piece(3).run(sender=buyer3, amount=sp.tez(2))
    market.buy_piece(4).run(sender=buyer3, amount=sp.tez(2))
    market.buy_piece(5).run(sender=buyer3, amount=sp.tez(2))
    
    # Verify different share tokens
    scenario.verify(
        share_contract.data.ledger[sp.pair(buyer3.address, 3)] == 2_000_000
    )
    scenario.verify(
        share_contract.data.ledger[sp.pair(buyer3.address, 4)] == 2_000_000
    )
    scenario.verify(
        share_contract.data.ledger[sp.pair(buyer3.address, 5)] == 2_000_000
    )


@sp.add_test(name="Integration - Full Workflow")
def test_full_integration():
    scenario = sp.test_scenario()
    scenario.h1("Full Integration Test - Realistic Workflow")
    
    # Actors
    admin = sp.test_account("Admin")
    artist1 = sp.test_account("Artist1")
    artist2 = sp.test_account("Artist2")
    collector1 = sp.test_account("Collector1")
    collector2 = sp.test_account("Collector2")
    collector3 = sp.test_account("Collector3")
    
    # Deploy all contracts
    share_contract = ShareFA2(admin=admin.address)
    scenario += share_contract
    
    market = FractionalArtMarketV1_FA2(share_fa2=share_contract.address)
    scenario += market
    
    nft_contract = MockNFT_FA2()
    scenario += nft_contract
    
    # Setup: transfer admin to market
    share_contract.set_admin(market.address).run(sender=admin)
    
    scenario.h2("Scenario: Two artists, multiple artworks, multiple collectors")
    
    # Artist 1 creates a gallery collection (15% cap per buyer)
    scenario.h3("1. Artist1 creates 'Gallery Collection' with 15% cap")
    market.create_collection(15).run(sender=artist1)
    
    # Artist 1 mints and lists 2 NFTs
    scenario.h3("2. Artist1 creates two pieces")
    for token_id in [0, 1]:
        nft_contract.mint(
            sp.record(to_=artist1.address, token_id=token_id)
        ).run(sender=artist1)
        
        nft_contract.update_operators([
            sp.variant("add_operator", sp.record(
                owner=artist1.address,
                operator=market.address,
                token_id=token_id
            ))
        ]).run(sender=artist1)
        
        market.create_piece_from_nft(
            sp.record(
                collection_id=0,
                nft_fa2=nft_contract.address,
                nft_token_id=token_id,
                price=sp.tez(20)
            )
        ).run(sender=artist1)
    
    # Artist 2 creates an exclusive collection (50% cap)
    scenario.h3("3. Artist2 creates 'Exclusive Collection' with 50% cap")
    market.create_collection(50).run(sender=artist2)
    
    nft_contract.mint(
        sp.record(to_=artist2.address, token_id=2)
    ).run(sender=artist2)
    
    nft_contract.update_operators([
        sp.variant("add_operator", sp.record(
            owner=artist2.address,
            operator=market.address,
            token_id=2
        ))
    ]).run(sender=artist2)
    
    market.create_piece_from_nft(
        sp.record(
            collection_id=1,
            nft_fa2=nft_contract.address,
            nft_token_id=2,
            price=sp.tez(10)
        )
    ).run(sender=artist2)
    
    # Collectors start buying
    scenario.h3("4. Collectors purchase shares in various pieces")
    
    # Piece 0 (Artist1, 20 tez, 15% cap = 3 tez max per buyer)
    market.buy_piece(0).run(sender=collector1, amount=sp.tez(3))
    market.buy_piece(0).run(sender=collector2, amount=sp.tez(3))
    market.buy_piece(0).run(sender=collector3, amount=sp.tez(2))
    
    # Piece 2 (Artist2, 10 tez, 50% cap = 5 tez max per buyer)
    market.buy_piece(2).run(sender=collector1, amount=sp.tez(5))
    market.buy_piece(2).run(sender=collector2, amount=sp.tez(5))
    
    # Verify piece 2 is fully funded and closed
    scenario.verify(market.data.pieces[2].closed == True)
    
    scenario.h3("5. Verify share ownership")
    # Collector1 should have shares in piece 0 and piece 2
    scenario.verify(
        share_contract.data.ledger[sp.pair(collector1.address, 0)] == 3_000_000
    )
    scenario.verify(
        share_contract.data.ledger[sp.pair(collector1.address, 2)] == 5_000_000
    )
    
    scenario.h3("6. Collector transfers shares to another collector")
    # Collector1 transfers some piece 0 shares to collector3
    share_contract.transfer([
        sp.record(
            from_=collector1.address,
            txs=[
                sp.record(
                    to_=collector3.address,
                    token_id=0,
                    amount=1_000_000  # 1 tez worth
                )
            ]
        )
    ]).run(sender=collector1)
    
    scenario.verify(
        share_contract.data.ledger[sp.pair(collector1.address, 0)] == 2_000_000
    )
    scenario.verify(
        share_contract.data.ledger[sp.pair(collector3.address, 0)] == 3_000_000  # 2 + 1 transferred
    )
    
    scenario.h3("7. Complete funding of piece 0")
    # Need 20 - 8 = 12 tez more
    # Max per buyer is 3 tez, so need at least 4 more buyers total
    buyer4 = sp.test_account("Buyer4")
    buyer5 = sp.test_account("Buyer5")
    buyer6 = sp.test_account("Buyer6")
    buyer7 = sp.test_account("Buyer7")
    
    market.buy_piece(0).run(sender=buyer4, amount=sp.tez(3))
    market.buy_piece(0).run(sender=buyer5, amount=sp.tez(3))
    market.buy_piece(0).run(sender=buyer6, amount=sp.tez(3))
    market.buy_piece(0).run(sender=buyer7, amount=sp.tez(3))
    
    scenario.verify(market.data.pieces[0].closed == True)
    scenario.verify(market.data.pieces[0].total_raised == sp.tez(20))
    
    scenario.h3("8. Verify total supply of shares")
    scenario.verify(share_contract.data.total_supply[0] == 20_000_000)
    scenario.verify(share_contract.data.total_supply[2] == 10_000_000)
    
    scenario.p("✅ Full integration test completed successfully!")


# Add compilation targets (optional, for completeness)
sp.add_compilation_target("test_mock_nft", MockNFT_FA2())
