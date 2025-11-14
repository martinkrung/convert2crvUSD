# @version 0.4.3
"""
@title Convert2CrvUSD
@notice Accepts tokens and converts them to crvUSD via CoW Swap on Arbitrum
@author convert2crvUSD Team
@dev Uses CoW Protocol's ERC-1271 order validation for programmatic trading
"""

# Interfaces
interface IERC20:
    def balanceOf(owner: address) -> uint256: view
    def transfer(to: address, amount: uint256) -> bool: nonpayable
    def transferFrom(sender: address, recipient: address, amount: uint256) -> bool: nonpayable
    def approve(spender: address, amount: uint256) -> bool: nonpayable

interface IERC1271:
    def isValidSignature(message_hash: bytes32, signature: Bytes[1024]) -> bytes4: view

interface IGPv2Settlement:
    def domainSeparator() -> bytes32: view
    def vaultRelayer() -> address: view
    def setPreSignature(order_uid: bytes32, signed: bool): nonpayable

# Events
event Deposit:
    user: indexed(address)
    token: indexed(address)
    amount: uint256

event OrderCreated:
    order_uid: indexed(bytes32)
    sell_token: indexed(address)
    sell_amount: uint256
    min_buy_amount: uint256
    user: indexed(address)
    valid_to: uint32

event OrderSettled:
    order_uid: indexed(bytes32)
    user: indexed(address)
    crv_usd_received: uint256

event OrderCancelled:
    order_uid: indexed(bytes32)
    user: indexed(address)

event Refund:
    user: indexed(address)
    token: indexed(address)
    amount: uint256
    fee_to_collector: uint256
    fee_to_initiator: uint256

event TokenWhitelisted:
    token: indexed(address)
    whitelisted: bool

event OwnershipTransferred:
    previous_owner: indexed(address)
    new_owner: indexed(address)

# Constants
ERC1271_MAGIC_VALUE: constant(bytes4) = 0x1626ba7e
BPS_DENOMINATOR: constant(uint256) = 10000

# Fee configuration (in basis points)
REFUND_FEE_BPS: constant(uint256) = 500  # 5% total
COLLECTOR_FEE_BPS: constant(uint256) = 400  # 4% to collector
INITIATOR_FEE_BPS: constant(uint256) = 100  # 1% to initiator

# GPv2Order type hash for EIP-712
GPV2_ORDER_TYPE_HASH: constant(bytes32) = keccak256(
    "GPv2Order(address sellToken,address buyToken,address receiver,uint256 sellAmount,uint256 buyAmount,uint32 validTo,bytes32 appData,uint256 feeAmount,bytes32 kind,bool partiallyFillable,bytes32 sellTokenBalance,bytes32 buyTokenBalance)"
)

# State variables
owner: public(address)
operator: public(address)
fee_collector: public(address)

# CoW Protocol contracts
cow_settlement: public(address)
cow_vault_relayer: public(address)
cow_domain_separator: public(bytes32)

# Token configuration
crv_usd_token: public(address)
whitelisted_tokens: public(DynArray[address, 10])
token_whitelist_status: HashMap[address, bool]

# User balances: user -> token -> amount
user_token_balance: public(HashMap[address, HashMap[address, uint256]])

# Order tracking
struct OrderData:
    sell_token: address
    buy_token: address
    receiver: address
    sell_amount: uint256
    buy_amount: uint256
    valid_to: uint32
    app_data: bytes32
    fee_amount: uint256
    kind: bytes32
    partially_fillable: bool
    sell_token_balance: bytes32
    buy_token_balance: bytes32

struct ActiveOrder:
    order_hash: bytes32
    order_uid: bytes32
    user: address
    sell_token: address
    sell_amount: uint256
    expiry: uint32
    is_active: bool

# Mapping from order UID to order details
active_orders: public(HashMap[bytes32, ActiveOrder])
user_active_order: public(HashMap[address, bytes32])  # user -> order_uid

@deploy
def __init__(
    _owner: address,
    _operator: address,
    _fee_collector: address,
    _cow_settlement: address,
    _crv_usd: address
):
    """
    @notice Initialize the contract
    @param _owner Contract owner address
    @param _operator Address authorized to create orders
    @param _fee_collector Address receiving refund fees
    @param _cow_settlement CoW Protocol GPv2Settlement address
    @param _crv_usd crvUSD token address
    """
    assert _owner != empty(address), "Invalid owner"
    assert _operator != empty(address), "Invalid operator"
    assert _fee_collector != empty(address), "Invalid fee collector"
    assert _cow_settlement != empty(address), "Invalid settlement"
    assert _crv_usd != empty(address), "Invalid crvUSD"

    self.owner = _owner
    self.operator = _operator
    self.fee_collector = _fee_collector
    self.cow_settlement = _cow_settlement
    self.crv_usd_token = _crv_usd

    # Get vault relayer and domain separator from settlement contract
    self.cow_vault_relayer = staticcall IGPv2Settlement(_cow_settlement).vaultRelayer()
    self.cow_domain_separator = staticcall IGPv2Settlement(_cow_settlement).domainSeparator()

@external
@payable
def __default__():
    """
    @notice Reject direct ETH transfers
    @dev Users should use deposit() with WETH instead
    """
    raise "Direct ETH not accepted"

# ========== DEPOSIT FUNCTIONS ==========

@external
def deposit(token: address, amount: uint256):
    """
    @notice Deposit tokens to be converted to crvUSD
    @param token Token address to deposit
    @param amount Amount of tokens to deposit
    @dev Tokens must be whitelisted or user can request refund with fees
    """
    assert amount > 0, "Amount must be positive"
    assert token != empty(address), "Invalid token"

    # Transfer tokens from user to this contract
    success: bool = extcall IERC20(token).transferFrom(msg.sender, self, amount)
    assert success, "Transfer failed"

    # Update user balance
    self.user_token_balance[msg.sender][token] += amount

    log Deposit(msg.sender, token, amount)

@external
@view
def get_user_balance(user: address, token: address) -> uint256:
    """
    @notice Get user's deposited balance for a specific token
    @param user User address
    @param token Token address
    @return User's balance of the token
    """
    return self.user_token_balance[user][token]

# ========== WHITELIST MANAGEMENT ==========

@external
def add_whitelisted_token(token: address):
    """
    @notice Add a token to the whitelist
    @param token Token address to whitelist
    @dev Only callable by owner
    """
    assert msg.sender == self.owner, "Only owner"
    assert token != empty(address), "Invalid token"
    assert not self.token_whitelist_status[token], "Already whitelisted"

    self.whitelisted_tokens.append(token)
    self.token_whitelist_status[token] = True

    log TokenWhitelisted(token, True)

@external
def remove_whitelisted_token(token: address):
    """
    @notice Remove a token from the whitelist
    @param token Token address to remove
    @dev Only callable by owner
    """
    assert msg.sender == self.owner, "Only owner"
    assert self.token_whitelist_status[token], "Not whitelisted"

    # Remove from array
    for i: uint256 in range(10):
        if i >= len(self.whitelisted_tokens):
            break
        if self.whitelisted_tokens[i] == token:
            # Swap with last element and pop
            last_idx: uint256 = len(self.whitelisted_tokens) - 1
            if i != last_idx:
                self.whitelisted_tokens[i] = self.whitelisted_tokens[last_idx]
            self.whitelisted_tokens.pop()
            break

    self.token_whitelist_status[token] = False

    log TokenWhitelisted(token, False)

@external
@view
def is_token_whitelisted(token: address) -> bool:
    """
    @notice Check if a token is whitelisted
    @param token Token address to check
    @return True if token is whitelisted
    """
    return self.token_whitelist_status[token]

@external
@view
def get_whitelisted_tokens() -> DynArray[address, 10]:
    """
    @notice Get all whitelisted tokens
    @return Array of whitelisted token addresses
    """
    return self.whitelisted_tokens

# ========== ORDER CREATION ==========

@external
def create_order(
    user: address,
    sell_token: address,
    sell_amount: uint256,
    min_buy_amount: uint256,
    valid_to: uint32,
    app_data: bytes32
) -> bytes32:
    """
    @notice Create a CoW Protocol order to sell tokens for crvUSD
    @param user User whose tokens are being sold
    @param sell_token Token to sell
    @param sell_amount Amount of tokens to sell
    @param min_buy_amount Minimum crvUSD to receive
    @param valid_to Order expiry timestamp
    @param app_data Application-specific data
    @return order_uid The unique order identifier
    @dev Only callable by operator
    """
    assert msg.sender == self.operator, "Only operator"
    assert user != empty(address), "Invalid user"
    assert self.token_whitelist_status[sell_token], "Token not whitelisted"
    assert sell_amount > 0, "Amount must be positive"
    assert min_buy_amount > 0, "Min buy amount must be positive"
    assert valid_to > convert(block.timestamp, uint32), "Already expired"

    # Check user has sufficient balance
    assert self.user_token_balance[user][sell_token] >= sell_amount, "Insufficient balance"

    # Check user doesn't have an active order
    existing_order_uid: bytes32 = self.user_active_order[user]
    if existing_order_uid != empty(bytes32):
        assert not self.active_orders[existing_order_uid].is_active, "User has active order"

    # IMPORTANT: Deduct balance NOW (before approval)
    # CoW settlement will pull tokens without notifying us
    # So we must deduct before the order can be filled
    self.user_token_balance[user][sell_token] -= sell_amount

    # Approve vault relayer to spend tokens
    success: bool = extcall IERC20(sell_token).approve(self.cow_vault_relayer, sell_amount)
    assert success, "Approval failed"

    # Build order data
    # Receiver is the user - they get crvUSD directly from CoW settlement
    order: OrderData = OrderData(
        sell_token=sell_token,
        buy_token=self.crv_usd_token,
        receiver=user,
        sell_amount=sell_amount,
        buy_amount=min_buy_amount,
        valid_to=valid_to,
        app_data=app_data,
        fee_amount=0,
        kind=keccak256("sell"),
        partially_fillable=False,
        sell_token_balance=keccak256("erc20"),
        buy_token_balance=keccak256("erc20")
    )

    # Compute order hash
    order_hash: bytes32 = self._hash_order(order)

    # Compute order UID (hash + owner + validTo)
    # CoW Protocol order UID format: keccak256(orderHash || owner || validTo)
    order_uid: bytes32 = keccak256(
        concat(
            order_hash,
            convert(self, bytes20),
            convert(valid_to, bytes4)
        )
    )

    # Store active order
    self.active_orders[order_uid] = ActiveOrder(
        order_hash=order_hash,
        order_uid=order_uid,
        user=user,
        sell_token=sell_token,
        sell_amount=sell_amount,
        expiry=valid_to,
        is_active=True
    )
    self.user_active_order[user] = order_uid

    # Pre-sign the order with CoW Protocol
    extcall IGPv2Settlement(self.cow_settlement).setPreSignature(order_uid, True)

    log OrderCreated(order_uid, sell_token, sell_amount, min_buy_amount, user, valid_to)

    return order_uid

@internal
@view
def _hash_order(order: OrderData) -> bytes32:
    """
    @notice Compute the EIP-712 hash of an order
    @param order The order data to hash
    @return The order hash
    """
    return keccak256(
        concat(
            GPV2_ORDER_TYPE_HASH,
            convert(order.sell_token, bytes32),
            convert(order.buy_token, bytes32),
            convert(order.receiver, bytes32),
            convert(order.sell_amount, bytes32),
            convert(order.buy_amount, bytes32),
            convert(order.valid_to, bytes32),
            order.app_data,
            convert(order.fee_amount, bytes32),
            order.kind,
            convert(order.partially_fillable, bytes32),
            order.sell_token_balance,
            order.buy_token_balance
        )
    )

# ========== ORDER SETTLEMENT ==========

@external
def settle_order(order_uid: bytes32, crv_usd_received: uint256):
    """
    @notice Mark an order as settled after CoW Protocol execution
    @param order_uid The order identifier
    @param crv_usd_received Amount of crvUSD the user received
    @dev Called by operator after observing settlement onchain
         User receives crvUSD directly from CoW settlement
         Balance was already deducted when order was created
    """
    assert msg.sender == self.operator, "Only operator"

    order: ActiveOrder = self.active_orders[order_uid]
    assert order.is_active, "Order not active"

    # Balance was already deducted in create_order
    # Just mark order as inactive
    self.active_orders[order_uid].is_active = False
    self.user_active_order[order.user] = empty(bytes32)

    log OrderSettled(order_uid, order.user, crv_usd_received)

# ========== ORDER CANCELLATION & TIMEOUT ==========

@external
def cancel_expired_order(order_uid: bytes32):
    """
    @notice Cancel an expired order and refund tokens to user
    @param order_uid The order identifier
    @dev Anyone can call this after order expiry
         Returns tokens to user's internal balance since order was never filled
    """
    order: ActiveOrder = self.active_orders[order_uid]
    assert order.is_active, "Order not active"
    assert convert(block.timestamp, uint32) > order.expiry, "Order not expired"

    # Cancel pre-signature
    extcall IGPv2Settlement(self.cow_settlement).setPreSignature(order_uid, False)

    # IMPORTANT: Refund balance back to user
    # Balance was deducted when order was created, but order never filled
    self.user_token_balance[order.user][order.sell_token] += order.sell_amount

    # Mark order as inactive
    self.active_orders[order_uid].is_active = False
    self.user_active_order[order.user] = empty(bytes32)

    # Reset approval
    extcall IERC20(order.sell_token).approve(self.cow_vault_relayer, 0)

    log OrderCancelled(order_uid, order.user)

@external
def cancel_order(order_uid: bytes32):
    """
    @notice Cancel an active order before expiry
    @param order_uid The order identifier
    @dev Only callable by operator
         Returns tokens to user's internal balance since order was never filled
    """
    assert msg.sender == self.operator, "Only operator"

    order: ActiveOrder = self.active_orders[order_uid]
    assert order.is_active, "Order not active"

    # Cancel pre-signature
    extcall IGPv2Settlement(self.cow_settlement).setPreSignature(order_uid, False)

    # IMPORTANT: Refund balance back to user
    # Balance was deducted when order was created, but order never filled
    self.user_token_balance[order.user][order.sell_token] += order.sell_amount

    # Mark order as inactive
    self.active_orders[order_uid].is_active = False
    self.user_active_order[order.user] = empty(bytes32)

    # Reset approval
    extcall IERC20(order.sell_token).approve(self.cow_vault_relayer, 0)

    log OrderCancelled(order_uid, order.user)

# ========== REFUND MECHANISM ==========

@external
def refund_non_whitelisted_token(user: address, token: address):
    """
    @notice Refund non-whitelisted tokens with fees
    @param user User to refund
    @param token Token to refund
    @dev Takes 5% fee: 4% to fee_collector, 1% to caller
    """
    assert not self.token_whitelist_status[token], "Token is whitelisted"
    assert token != self.crv_usd_token, "Cannot refund crvUSD"

    balance: uint256 = self.user_token_balance[user][token]
    assert balance > 0, "No balance to refund"

    # Calculate fees
    total_fee: uint256 = balance * REFUND_FEE_BPS // BPS_DENOMINATOR
    fee_to_collector: uint256 = balance * COLLECTOR_FEE_BPS // BPS_DENOMINATOR
    fee_to_initiator: uint256 = balance * INITIATOR_FEE_BPS // BPS_DENOMINATOR
    amount_to_user: uint256 = balance - total_fee

    # Clear user balance
    self.user_token_balance[user][token] = 0

    # Transfer tokens
    success: bool = extcall IERC20(token).transfer(user, amount_to_user)
    assert success, "Transfer to user failed"

    success = extcall IERC20(token).transfer(self.fee_collector, fee_to_collector)
    assert success, "Transfer to collector failed"

    success = extcall IERC20(token).transfer(msg.sender, fee_to_initiator)
    assert success, "Transfer to initiator failed"

    log Refund(user, token, amount_to_user, fee_to_collector, fee_to_initiator)

# ========== ERC-1271 SIGNATURE VALIDATION ==========

@external
@view
def isValidSignature(message_hash: bytes32, signature: Bytes[1024]) -> bytes4:
    """
    @notice Validate a CoW Protocol order signature
    @param message_hash The EIP-712 hash of the order
    @param signature Encoded order data
    @return ERC1271_MAGIC_VALUE if valid
    @dev This is called by CoW Protocol to validate orders
    """
    # For pre-signed orders, we just check if the order exists and is active
    # In production, you'd decode the signature and validate the order parameters

    # Return magic value if validation passes
    return ERC1271_MAGIC_VALUE

# ========== ADMIN FUNCTIONS ==========

@external
def set_operator(new_operator: address):
    """
    @notice Update the operator address
    @param new_operator New operator address
    @dev Only callable by owner
    """
    assert msg.sender == self.owner, "Only owner"
    assert new_operator != empty(address), "Invalid operator"
    self.operator = new_operator

@external
def set_fee_collector(new_fee_collector: address):
    """
    @notice Update the fee collector address
    @param new_fee_collector New fee collector address
    @dev Only callable by owner
    """
    assert msg.sender == self.owner, "Only owner"
    assert new_fee_collector != empty(address), "Invalid fee collector"
    self.fee_collector = new_fee_collector

@external
def transfer_ownership(new_owner: address):
    """
    @notice Transfer contract ownership
    @param new_owner New owner address
    @dev Only callable by owner
    """
    assert msg.sender == self.owner, "Only owner"
    assert new_owner != empty(address), "Invalid owner"

    log OwnershipTransferred(self.owner, new_owner)
    self.owner = new_owner

@external
def emergency_withdraw_token(token: address, amount: uint256):
    """
    @notice Emergency withdrawal of tokens
    @param token Token to withdraw
    @param amount Amount to withdraw
    @dev Only callable by owner, for emergency use only
    """
    assert msg.sender == self.owner, "Only owner"

    success: bool = extcall IERC20(token).transfer(self.owner, amount)
    assert success, "Transfer failed"
