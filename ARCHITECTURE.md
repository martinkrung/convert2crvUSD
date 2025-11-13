# Convert2crvUSD Architecture

## Overview
Smart contract system on Arbitrum that accepts various tokens and converts them to crvUSD via CoW Swap.

## Contract Architecture

### Core Components

#### 1. User Deposit System
- Users can send whitelisted tokens directly to the contract
- Contract tracks internal balances per user per token
- Deposits are recorded in `user_token_balance[user][token]`

#### 2. Token Whitelist
- Maintains list of accepted tokens: WETH, USDC, CRV
- Non-whitelisted tokens can be refunded with fees
- Whitelist managed by contract owner

#### 3. CoW Protocol Integration
- Creates orders to sell tokens for crvUSD
- Uses ERC-1271 signature validation
- Approves GPv2VaultRelayer to spend tokens
- Tracks orders with timeouts

#### 4. Fee System
- **Refund Fee**: 500 basis points (5%)
  - 400 bps → Fee collector
  - 100 bps → Refund initiator (gas compensation)

### Variable Naming Convention

All variables use `snake_case` following Vyper conventions and CoW Protocol terminology:

#### User Data
- `user_token_balance`: Mapping of user → token → balance
- `user_deposits`: Tracking deposit history

#### Token Management
- `whitelisted_tokens`: DynArray of accepted token addresses
- `token_whitelist_status`: Mapping for O(1) whitelist checks
- `crv_usd_token`: Target token for conversions

#### Order Management
- `order_creator`: Who initiated each order
- `order_expiry`: Timestamp when order expires
- `order_sell_token`: Token being sold
- `order_sell_amount`: Amount being sold
- `active_order_uid`: Currently active order identifier

#### CoW Protocol
- `cow_settlement`: GPv2Settlement contract
- `cow_vault_relayer`: Authorized token transferrer
- `cow_domain_separator`: EIP-712 domain for signatures

#### Fee Configuration
- `fee_collector`: Address receiving protocol fees
- `refund_fee_bps`: Total refund fee (500)
- `collector_fee_bps`: Fee collector portion (400)
- `initiator_fee_bps`: Refund initiator portion (100)

#### Access Control
- `owner`: Contract administrator
- `operator`: Address authorized to create orders

### Order Lifecycle

1. **Deposit**: User sends whitelisted token to contract
2. **Order Creation**: Operator creates CoW order via API
3. **Order Validation**: Contract validates via ERC-1271
4. **Settlement**: CoW solver fills order, sends crvUSD
5. **Timeout**: If order expires unfilled, user can reclaim

### Security Features

1. **Reentrancy Protection**: Follow checks-effects-interactions
2. **Access Control**: Owner and operator roles
3. **Order Validation**: ERC-1271 signature checks
4. **Timeout Protection**: Orders expire after deadline
5. **Balance Tracking**: Accurate per-user accounting

## CoW Protocol Integration Details

### GPv2 Order Structure
```
struct GPv2Order:
    sell_token: address
    buy_token: address (always crvUSD)
    receiver: address (this contract)
    sell_amount: uint256
    buy_amount: uint256 (minimum acceptable)
    valid_to: uint32 (expiry timestamp)
    app_data: bytes32 (metadata)
    fee_amount: uint256
    kind: bytes32 (sell or buy)
    partially_fillable: bool
    sell_token_balance: bytes32 (erc20/external)
    buy_token_balance: bytes32 (erc20)
```

### ERC-1271 Implementation
- Validate order parameters match stored order data
- Check order hasn't expired
- Verify caller is authorized
- Return magic value `0x1626ba7e` if valid

### Contract Addresses (Arbitrum)
- **GPv2Settlement**: `0x9008D19f58AAbD9eD0D60971565AA8510560ab41`
- **ComposableCoW**: `0xfdaFc9d1902f4e0b84f65F49f244b32b31013b74`

## Deployment Flow

1. Deploy contract with owner, operator, fee_collector
2. Set whitelisted tokens (WETH, USDC, CRV)
3. Set crvUSD address
4. Set CoW Protocol addresses
5. Verify on Arbiscan
6. Test deposits and orders

## Testing Strategy

### Unit Tests
- Deposit functionality
- Balance tracking
- Whitelist management
- Fee calculations
- Access control

### Integration Tests
- Full order lifecycle
- ERC-1271 validation
- CoW Protocol interaction
- Timeout handling
- Refund mechanism

### Edge Cases
- Zero amounts
- Invalid tokens
- Expired orders
- Insufficient balances
- Reentrancy attempts
