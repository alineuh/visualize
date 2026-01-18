import smartpy as sp

class ShareFA2(sp.Contract):
    """
    Minimal FA2-like fungible token for shares.
    - Balances are nat
    - Operators supported
    - Mint is restricted to admin (the Market contract)
    - set_admin is used to hand admin rights to the Market after deployment
    """

    def __init__(self, admin):
        self.init(
            admin=admin,
            # (owner, token_id) -> balance
            ledger=sp.big_map(tkey=sp.TPair(sp.TAddress, sp.TNat), tvalue=sp.TNat),
            # (owner, operator, token_id) -> unit
            operators=sp.big_map(
                tkey=sp.TRecord(owner=sp.TAddress, operator=sp.TAddress, token_id=sp.TNat)
                    .layout(("owner", ("operator", "token_id"))),
                tvalue=sp.TUnit
            ),
            # token_id -> total_supply
            total_supply=sp.big_map(tkey=sp.TNat, tvalue=sp.TNat)
        )

    def _operator_key(self, owner, operator, token_id):
        return sp.record(owner=owner, operator=operator, token_id=token_id)

    def _is_operator(self, owner, operator, token_id):
        return self.data.operators.contains(self._operator_key(owner, operator, token_id))

    @sp.entry_point
    def set_admin(self, new_admin):
        sp.set_type(new_admin, sp.TAddress)
        sp.verify(sp.sender == self.data.admin, "NOT_ADMIN")
        self.data.admin = new_admin

    @sp.entry_point
    def update_operators(self, params):
        """
        params: list( variant(add_operator | remove_operator) )
        """
        t_op = sp.TRecord(owner=sp.TAddress, operator=sp.TAddress, token_id=sp.TNat)\
            .layout(("owner", ("operator", "token_id")))
        t_item = sp.TVariant(add_operator=t_op, remove_operator=t_op)

        sp.set_type(params, sp.TList(t_item))

        sp.for it in params:
            sp.if it.is_variant("add_operator"):
                r = it.open_variant("add_operator")
                sp.verify(sp.sender == r.owner, "NOT_OWNER")
                self.data.operators[self._operator_key(r.owner, r.operator, r.token_id)] = sp.unit
            sp.else:
                r = it.open_variant("remove_operator")
                sp.verify(sp.sender == r.owner, "NOT_OWNER")
                key = self._operator_key(r.owner, r.operator, r.token_id)
                sp.if self.data.operators.contains(key):
                    del self.data.operators[key]

    @sp.entry_point
    def transfer(self, txs):
        """
        txs: list({
          from_: address,
          txs: list({ to_: address, token_id: nat, amount: nat })
        })
        """
        t_tx = sp.TRecord(to_=sp.TAddress, token_id=sp.TNat, amount=sp.TNat)\
            .layout(("to_", ("token_id", "amount")))
        t_item = sp.TRecord(from_=sp.TAddress, txs=sp.TList(t_tx))\
            .layout(("from_", "txs"))
        sp.set_type(txs, sp.TList(t_item))

        sp.for batch in txs:
            sp.for tx in batch.txs:
                sp.verify(
                    (sp.sender == batch.from_) | self._is_operator(batch.from_, sp.sender, tx.token_id),
                    "NOT_OPERATOR"
                )

                from_key = sp.pair(batch.from_, tx.token_id)
                to_key = sp.pair(tx.to_, tx.token_id)

                from_bal = self.data.ledger.get(from_key, 0)
                sp.verify(from_bal >= tx.amount, "INSUFFICIENT_BALANCE")

                self.data.ledger[from_key] = from_bal - tx.amount
                self.data.ledger[to_key] = self.data.ledger.get(to_key, 0) + tx.amount

    @sp.entry_point
    def mint(self, params):
        """
        params: { to_, token_id, amount }
        Only admin can mint (Market).
        """
        sp.set_type(params, sp.TRecord(to_=sp.TAddress, token_id=sp.TNat, amount=sp.TNat)
                             .layout(("to_", ("token_id", "amount"))))
        sp.verify(sp.sender == self.data.admin, "NOT_ADMIN")
        sp.verify(params.amount > 0, "ZERO_MINT")

        key = sp.pair(params.to_, params.token_id)
        self.data.ledger[key] = self.data.ledger.get(key, 0) + params.amount
        self.data.total_supply[params.token_id] = self.data.total_supply.get(params.token_id, 0) + params.amount


# ------------------------
# Taqueria compilation target 
# ------------------------
sp.add_compilation_target(
    "share_fa2",
    ShareFA2(admin=sp.address("tz1-admin-placeholder-address-1234"))
)
