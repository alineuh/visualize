import smartpy as sp

# Minimal FA2 transfer param type for an external NFT contract
FA2_TransferTx = sp.TRecord(
    to_=sp.TAddress,
    token_id=sp.TNat,
    amount=sp.TNat
).layout(("to_", ("token_id", "amount")))

FA2_TransferItem = sp.TRecord(
    from_=sp.TAddress,
    txs=sp.TList(FA2_TransferTx)
).layout(("from_", "txs"))

FA2_TransferParam = sp.TList(FA2_TransferItem)


class FractionalArtMarketV1_FA2(sp.Contract):
    """
    v1 (FA2-based shares):
    - Artist creates collections (capShare% per collection)
    - Artist escrows an existing FA2 NFT into this contract to create a piece sale
    - Buyers fund in tez (capped per buyer) and receive FA2 share tokens (minted)
    - Shares minted 1:1 with contributed mutez (converted to nat)
    - Piece closes when fully funded
    """

    def __init__(self, share_fa2):
        self.init(
            share_fa2=share_fa2,

            next_collection_id=0,
            next_piece_id=0,
            next_share_token_id=0,

            # collection_id -> { artist, cap_percent }
            collections=sp.big_map(
                tkey=sp.TNat,
                tvalue=sp.TRecord(artist=sp.TAddress, cap_percent=sp.TNat)
                    .layout(("artist", "cap_percent"))
            ),

            # piece_id -> { collection_id, price, total_raised, closed, nft_fa2, nft_token_id, share_token_id }
            pieces=sp.big_map(
                tkey=sp.TNat,
                tvalue=sp.TRecord(
                    collection_id=sp.TNat,
                    price=sp.TMutez,
                    total_raised=sp.TMutez,
                    closed=sp.TBool,
                    nft_fa2=sp.TAddress,
                    nft_token_id=sp.TNat,
                    share_token_id=sp.TNat
                ).layout(("collection_id", ("price", ("total_raised", ("closed", ("nft_fa2", ("nft_token_id", "share_token_id")))))))
            ),

            # (piece_id, buyer) -> contributed mutez
            contributions=sp.big_map(
                tkey=sp.TPair(sp.TNat, sp.TAddress),
                tvalue=sp.TMutez
            )
        )

    # --------------------
    # Artist actions
    # --------------------

    @sp.entry_point
    def create_collection(self, cap_percent):
        sp.set_type(cap_percent, sp.TNat)
        sp.verify(cap_percent >= 1, "CAP_TOO_LOW")
        sp.verify(cap_percent <= 100, "CAP_TOO_HIGH")

        cid = self.data.next_collection_id
        self.data.next_collection_id += 1

        self.data.collections[cid] = sp.record(
            artist=sp.sender,
            cap_percent=cap_percent
        )

    @sp.entry_point
    def create_piece_from_nft(self, params):
        """
        params:
          - collection_id
          - nft_fa2 (FA2 contract address of the NFT)
          - nft_token_id
          - price (mutez)

        Requires:
          - sender is the collection artist
          - artist has set this Market contract as operator in the NFT FA2 contract

        Effect:
          - transfers NFT (amount=1) from artist -> market escrow
          - creates a piece sale
          - allocates a new share_token_id used in ShareFA2
        """
        sp.set_type(params, sp.TRecord(
            collection_id=sp.TNat,
            nft_fa2=sp.TAddress,
            nft_token_id=sp.TNat,
            price=sp.TMutez
        ).layout(("collection_id", ("nft_fa2", ("nft_token_id", "price")))))

        sp.verify(self.data.collections.contains(params.collection_id), "NO_COLLECTION")
        col = self.data.collections[params.collection_id]
        sp.verify(sp.sender == col.artist, "NOT_ARTIST")
        sp.verify(params.price > sp.mutez(0), "BAD_PRICE")

        # Escrow the NFT: transfer 1 from artist -> this contract
        c_transfer = sp.contract(FA2_TransferParam, params.nft_fa2, entry_point="transfer").open_some("BAD_NFT_FA2")
        sp.transfer(
            [sp.record(from_=sp.sender, txs=[sp.record(to_=sp.self_address, token_id=params.nft_token_id, amount=1)])],
            sp.mutez(0),
            c_transfer
        )

        pid = self.data.next_piece_id
        self.data.next_piece_id += 1

        stid = self.data.next_share_token_id
        self.data.next_share_token_id += 1

        self.data.pieces[pid] = sp.record(
            collection_id=params.collection_id,
            price=params.price,
            total_raised=sp.mutez(0),
            closed=False,
            nft_fa2=params.nft_fa2,
            nft_token_id=params.nft_token_id,
            share_token_id=stid
        )

    # --------------------
    # Buyer action
    # --------------------

    @sp.entry_point
    def buy_piece(self, piece_id):
        sp.set_type(piece_id, sp.TNat)
        sp.verify(self.data.pieces.contains(piece_id), "NO_PIECE")

        p = self.data.pieces[piece_id]
        sp.verify(~p.closed, "PIECE_CLOSED")
        sp.verify(sp.amount > sp.mutez(0), "SEND_TEZ")

        col = self.data.collections[p.collection_id]
        cap_amount = sp.split_tokens(p.price, col.cap_percent, 100)

        key = sp.pair(piece_id, sp.sender)
        already = self.data.contributions.get(key, sp.mutez(0))

        sp.verify(already + sp.amount <= cap_amount, "OVER_CAP_SHARE")
        sp.verify(p.total_raised + sp.amount <= p.price, "OVER_PRICE")

        # Accounting
        self.data.contributions[key] = already + sp.amount
        self.data.pieces[piece_id].total_raised = p.total_raised + sp.amount

        # Mint shares 1:1 with contributed mutez
        mint_amount = sp.utils.mutez_to_nat(sp.amount)

        c_mint = sp.contract(
            sp.TRecord(to_=sp.TAddress, token_id=sp.TNat, amount=sp.TNat).layout(("to_", ("token_id", "amount"))),
            self.data.share_fa2,
            entry_point="mint"
        ).open_some("BAD_SHARE_FA2")

        sp.transfer(
            sp.record(to_=sp.sender, token_id=p.share_token_id, amount=mint_amount),
            sp.mutez(0),
            c_mint
        )

        # v1 behavior: pay artist immediately
        sp.send(col.artist, sp.amount)

        # Close when fully funded
        sp.if self.data.pieces[piece_id].total_raised == p.price:
            self.data.pieces[piece_id].closed = True

    # --------------------
    # Views (read helpers)
    # --------------------

    @sp.onchain_view()
    def get_collection(self, collection_id):
        sp.set_type(collection_id, sp.TNat)
        sp.verify(self.data.collections.contains(collection_id), "NO_COLLECTION")
        sp.result(self.data.collections[collection_id])

    @sp.onchain_view()
    def get_piece(self, piece_id):
        sp.set_type(piece_id, sp.TNat)
        sp.verify(self.data.pieces.contains(piece_id), "NO_PIECE")
        sp.result(self.data.pieces[piece_id])

    @sp.onchain_view()
    def get_user_contribution(self, params):
        sp.set_type(params, sp.TRecord(piece_id=sp.TNat, user=sp.TAddress).layout(("piece_id", "user")))
        sp.result(self.data.contributions.get(sp.pair(params.piece_id, params.user), sp.mutez(0)))

    @sp.onchain_view()
    def get_cap_amount(self, piece_id):
        sp.set_type(piece_id, sp.TNat)
        sp.verify(self.data.pieces.contains(piece_id), "NO_PIECE")
        p = self.data.pieces[piece_id]
        col = self.data.collections[p.collection_id]
        sp.result(sp.split_tokens(p.price, col.cap_percent, 100))


# ------------------------
# Taqueria compilation target (ADD THIS AT THE BOTTOM)
# ------------------------
sp.add_compilation_target(
    "market_v1",
    FractionalArtMarketV1_FA2(share_fa2=sp.address("KT1-share-placeholder-address-1234"))
)
