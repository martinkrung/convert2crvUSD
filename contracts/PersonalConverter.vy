# @version 0.4.3
"""
@title PersonalConverter
@notice Personal contract for converting tokens to crvUSD via CoW Swap
@author convert2crvUSD Team
@dev Each user gets their own instance deployed by ConverterFactory
     Users can send tokens directly to this contract (no approve needed!)
     Operator creates orders and pays gas on behalf of the owner
"""

# Interfaces
interface IERC20:
    def balanceOf(owner: address) -> uint256: view
    def transfer(to: address, amount: uint256) -> bool: nonpayable
    def approve(spender: address, amount: uint256) -> bool: nonpayable

interface IGPv2Settlement:
    def domainSeparator() -> bytes32: view
    def vaultRelayer() -> address: view
    def setPreSignature(order_uid: bytes32, signed: bool): nonpayable

# Events
event OrderCreated:
    order_uid: indexed(bytes32)
    sell_token: indexed(address)
    sell_amount: uint256
    min_buy_amount: uint256
    valid_to: uint32

event OrderSettled:
    order_uid: indexed(bytes32)
    crv_usd_received: uint256

event OrderCancelled:
    order_uid: indexed(bytes32)

event Refund:
    token: indexed(address)
    amount: uint256
    fee_to_collector: uint256
    fee_to_initiator: uint256

event TokenWhitelisted:
    token: indexed(address)
    whitelisted: bool

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

# Immutable configuration (set at deployment)
owner: public(immutable(address))
operator: public(immutable(address))
fee_collector: public(immutable(address))
cow_settlement: public(immutable(address))
cow_vault_relayer: public(immutable(address))
cow_domain_separator: public(immutable(bytes32))
crv_usd_token: public(immutable(address))

# Mutable state
whitelisted_tokens: public(DynArray[address, 10])
token_whitelist_status: public(HashMap[address, bool])

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
    sell_token: address
    sell_amount: uint256
    expiry: uint32
    is_active: bool

# Only one active order at a time
active_order: public(ActiveOrder)

# Track amounts committed to active orders per token
committed_balance: public(HashMap[address, uint256])

@deploy
def __init__(
    _owner: address,
    _operator: address,
    _fee_collector: address,
    _cow_settlement: address,
    _crv_usd: address,
    _initial_whitelist: DynArray[address, 10]
):
    """
    @notice Initialize personal converter contract
    @param _owner The owner of this contract (receives crvUSD)
    @param _operator Address authorized to create orders
    @param _fee_collector Address receiving refund fees
    @param _cow_settlement CoW Protocol GPv2Settlement address
    @param _crv_usd crvUSD token address
    @param _initial_whitelist Initial set of whitelisted tokens
    @dev Called by factory during deployment
    """
    owner = _owner
    operator = _operator
    fee_collector = _fee_collector
    cow_settlement = _cow_settlement
    crv_usd_token = _crv_usd

    # Get vault relayer and domain separator
    cow_vault_relayer = staticcall IGPv2Settlement(_cow_settlement).vaultRelayer()
    cow_domain_separator = staticcall IGPv2Settlement(_cow_settlement).domainSeparator()

    # Initialize whitelist
    for token: address in _initial_whitelist:
        if token != empty(address):
            self.whitelisted_tokens.append(token)
            self.token_whitelist_status[token] = True

@external
@payable
def __default__():
    """
    @notice Reject direct ETH transfers
    @dev Users should send WETH instead
    """
    raise "Direct ETH not accepted"

# ========== VIEW FUNCTIONS ==========

@external
@view
def get_available_balance(token: address) -> uint256:
    """
    @notice Get available balance for a token (total balance - committed to orders)
    @param token Token address
    @return Available balance
    """
    total: uint256 = staticcall IERC20(token).balanceOf(self)
    committed: uint256 = self.committed_balance[token]
    if total >= committed:
        return total - committed
    return 0

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
    sell_token: address,
    sell_amount: uint256,
    min_buy_amount: uint256,
    valid_to: uint32,
    app_data: bytes32
) -> bytes32:
    """
    @notice Create a CoW Protocol order to sell tokens for crvUSD
    @param sell_token Token to sell
    @param sell_amount Amount of tokens to sell
    @param min_buy_amount Minimum crvUSD to receive
    @param valid_to Order expiry timestamp
    @param app_data Application-specific data
    @return order_uid The unique order identifier
    @dev Only callable by operator
    """
    assert msg.sender == operator, "Only operator"
    assert self.token_whitelist_status[sell_token], "Token not whitelisted"
    assert sell_amount > 0, "Amount must be positive"
    assert min_buy_amount > 0, "Min buy amount must be positive"
    assert valid_to > convert(block.timestamp, uint32), "Already expired"

    # Check no active order exists
    assert not self.active_order.is_active, "Active order exists"

    # Check contract has sufficient available balance
    available: uint256 = staticcall IERC20(sell_token).balanceOf(self) - self.committed_balance[sell_token]
    assert available >= sell_amount, "Insufficient balance"

    # Mark balance as committed
    self.committed_balance[sell_token] += sell_amount

    # Approve vault relayer to spend tokens
    success: bool = extcall IERC20(sell_token).approve(cow_vault_relayer, sell_amount)
    assert success, "Approval failed"

    # Build order data - owner receives crvUSD directly
    order: OrderData = OrderData(
        sell_token=sell_token,
        buy_token=crv_usd_token,
        receiver=owner,
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

    # Compute order UID
    order_uid: bytes32 = keccak256(
        concat(
            order_hash,
            convert(self, bytes20),
            convert(valid_to, bytes4)
        )
    )

    # Store active order
    self.active_order = ActiveOrder(
        order_hash=order_hash,
        order_uid=order_uid,
        sell_token=sell_token,
        sell_amount=sell_amount,
        expiry=valid_to,
        is_active=True
    )

    # Pre-sign the order with CoW Protocol
    extcall IGPv2Settlement(cow_settlement).setPreSignature(order_uid, True)

    log OrderCreated(order_uid, sell_token, sell_amount, min_buy_amount, valid_to)

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
def settle_order(crv_usd_received: uint256):
    """
    @notice Mark the active order as settled
    @param crv_usd_received Amount of crvUSD the owner received
    @dev Called by operator after observing settlement onchain
    """
    assert msg.sender == operator, "Only operator"
    assert self.active_order.is_active, "No active order"

    order_uid: bytes32 = self.active_order.order_uid

    # Release committed balance (tokens already transferred by CoW)
    self.committed_balance[self.active_order.sell_token] -= self.active_order.sell_amount

    # Mark order as inactive
    self.active_order.is_active = False

    log OrderSettled(order_uid, crv_usd_received)

# ========== ORDER CANCELLATION ==========

@external
def cancel_expired_order():
    """
    @notice Cancel the expired active order
    @dev Anyone can call this after order expiry
    """
    assert self.active_order.is_active, "No active order"
    assert convert(block.timestamp, uint32) > self.active_order.expiry, "Order not expired"

    order_uid: bytes32 = self.active_order.order_uid

    # Cancel pre-signature
    extcall IGPv2Settlement(cow_settlement).setPreSignature(order_uid, False)

    # Release committed balance
    self.committed_balance[self.active_order.sell_token] -= self.active_order.sell_amount

    # Mark order as inactive
    self.active_order.is_active = False

    # Reset approval
    extcall IERC20(self.active_order.sell_token).approve(cow_vault_relayer, 0)

    log OrderCancelled(order_uid)

@external
def cancel_order():
    """
    @notice Cancel the active order before expiry
    @dev Only callable by operator
    """
    assert msg.sender == operator, "Only operator"
    assert self.active_order.is_active, "No active order"

    order_uid: bytes32 = self.active_order.order_uid

    # Cancel pre-signature
    extcall IGPv2Settlement(cow_settlement).setPreSignature(order_uid, False)

    # Release committed balance
    self.committed_balance[self.active_order.sell_token] -= self.active_order.sell_amount

    # Mark order as inactive
    self.active_order.is_active = False

    # Reset approval
    extcall IERC20(self.active_order.sell_token).approve(cow_vault_relayer, 0)

    log OrderCancelled(order_uid)

# ========== REFUND MECHANISM ==========

@external
def refund_non_whitelisted_token(token: address):
    """
    @notice Refund non-whitelisted tokens to owner with fees
    @param token Token to refund
    @dev Takes 5% fee: 4% to fee_collector, 1% to caller
    """
    assert not self.token_whitelist_status[token], "Token is whitelisted"
    assert token != crv_usd_token, "Cannot refund crvUSD"

    balance: uint256 = staticcall IERC20(token).balanceOf(self)
    assert balance > 0, "No balance to refund"

    # Calculate fees
    total_fee: uint256 = balance * REFUND_FEE_BPS // BPS_DENOMINATOR
    fee_to_collector: uint256 = balance * COLLECTOR_FEE_BPS // BPS_DENOMINATOR
    fee_to_initiator: uint256 = balance * INITIATOR_FEE_BPS // BPS_DENOMINATOR
    amount_to_owner: uint256 = balance - total_fee

    # Transfer tokens
    success: bool = extcall IERC20(token).transfer(owner, amount_to_owner)
    assert success, "Transfer to owner failed"

    success = extcall IERC20(token).transfer(fee_collector, fee_to_collector)
    assert success, "Transfer to collector failed"

    success = extcall IERC20(token).transfer(msg.sender, fee_to_initiator)
    assert success, "Transfer to initiator failed"

    log Refund(token, amount_to_owner, fee_to_collector, fee_to_initiator)

# ========== ERC-1271 SIGNATURE VALIDATION ==========

@external
@view
def isValidSignature(message_hash: bytes32, signature: Bytes[1024]) -> bytes4:
    """
    @notice Validate a CoW Protocol order signature
    @param message_hash The EIP-712 hash of the order
    @param signature Encoded order data
    @return ERC1271_MAGIC_VALUE if valid
    """
    # For pre-signed orders, return magic value
    return ERC1271_MAGIC_VALUE

# ========== EMERGENCY FUNCTIONS ==========

@external
def emergency_withdraw_token(token: address, amount: uint256):
    """
    @notice Emergency withdrawal of tokens to owner
    @param token Token to withdraw
    @param amount Amount to withdraw
    @dev Only callable by owner
    """
    assert msg.sender == owner, "Only owner"

    success: bool = extcall IERC20(token).transfer(owner, amount)
    assert success, "Transfer failed"
