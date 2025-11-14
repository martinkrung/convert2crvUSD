# Factory Pattern - Convert2CrvUSD

## Overview

The Convert2CrvUSD project uses a **factory pattern** to enable users to send tokens directly to a contract address without requiring `approve()` calls. This solves the original design goal: **"just send tokens to a contract"**.

## Architecture

### Components

1. **ConverterFactory.vy** - Factory contract that:
   - Deploys personal converter contracts for each user
   - Manages global configuration (operator, fee collector, whitelist)
   - Tracks all deployed personal converters

2. **PersonalConverter.vy** - Per-user contract that:
   - Has a fixed owner (the user)
   - Accepts direct token transfers
   - Allows operator to create CoW orders on behalf of the owner
   - Sends crvUSD directly to the owner
   - Handles order cancellation and refunds

3. **Blueprint Pattern** - PersonalConverter is deployed as a blueprint once, then all personal converters are cheap clones deployed via `create_from_blueprint()`

## How It Works

### 1. Initial Setup (One-time)

```
┌─────────────────┐
│ Deploy Blueprint│  <- PersonalConverter bytecode
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Deploy Factory  │  <- ConverterFactory with blueprint address
└─────────────────┘
```

### 2. User Onboarding

```
User A wants to convert tokens to crvUSD
         │
         v
Factory.deploy_personal_converter(User A)
         │
         v
   User A gets their own PersonalConverter contract
   Address: 0xABCD...
```

### 3. Token Conversion Flow

```
Step 1: User sends WETH directly (NO approve needed!)
┌──────┐
│User A│  --WETH--> [PersonalConverter A: 0xABCD...]
└──────┘

Step 2: Operator creates CoW order
┌─────────┐
│Operator │  --create_order()--> [PersonalConverter A]
└─────────┘                      │
                                 v
                          Order created & approved

Step 3: CoW solver executes trade
[CoW Settlement]  <--WETH--  [PersonalConverter A]
       │
       v
   crvUSD sent directly to User A
```

## Key Benefits

1. **No Approve Required**: Users just send tokens directly to their personal converter
2. **Simple UX**: Only one transaction needed: `token.transfer(my_converter, amount)`
3. **Isolated Balances**: Each user has their own contract - no multi-user accounting complexity
4. **Gas Efficient**: Blueprint pattern makes deployment cheap (~60k gas per user)

## Usage Examples

### Deploy a Personal Converter

```python
import boa

# Load factory
factory = boa.load_partial("contracts/ConverterFactory.vy").at(FACTORY_ADDRESS)

# Deploy personal converter for user
user_address = "0x1234..."
converter_address = factory.deploy_personal_converter(user_address)

print(f"User's personal converter: {converter_address}")
```

### User Sends Tokens

```python
# User perspective - Just send tokens!
from eth_account import Account

user = Account.from_key(PRIVATE_KEY)
weth = boa.load_partial("interfaces/IERC20.vyi").at(WETH_ADDRESS)

# Get my personal converter address
my_converter = factory.get_user_converter(user.address)

# Send WETH directly to my converter (no approve!)
with boa.env.prank(user.address):
    weth.transfer(my_converter, 5 * 10**18)  # Send 5 WETH
```

### Operator Creates Order

```python
# Operator perspective
operator = Account.from_key(OPERATOR_KEY)
converter = boa.load_partial("contracts/PersonalConverter.vy").at(user_converter)

# Create CoW order
with boa.env.prank(operator.address):
    order_uid = converter.create_order(
        weth.address,           # sell WETH
        5 * 10**18,             # sell 5 WETH
        7500 * 10**18,          # min 7500 crvUSD
        int(time.time()) + 3600,  # expires in 1 hour
        b"\x00" * 32            # app data
    )
```

### User Receives crvUSD

The user receives crvUSD directly from CoW Settlement - no additional transaction needed!

```python
crv_usd = boa.load_partial("interfaces/IERC20.vyi").at(CRV_USD_ADDRESS)
balance = crv_usd.balanceOf(user.address)
print(f"User received: {balance / 10**18} crvUSD")
```

## Deployment

### Deploy Factory System

```bash
# 1. Ensure environment is configured
cp .env_arbitrum.example .env_arbitrum
# Edit .env_arbitrum with your values

# 2. Run deployment script
python scripts/deploy_factory.py
```

This will:
1. Deploy PersonalConverter blueprint
2. Deploy ConverterFactory
3. Initialize with WETH, USDC, CRV whitelist
4. Save addresses to `deployment_factory.json`

### Deploy Personal Converter for User

```bash
# Using boa interact script
python scripts/boa_interact.py
# Select: "Deploy personal converter for user"
# Enter user address
```

Or programmatically:

```python
factory.deploy_personal_converter(user_address)
```

## Comparison: Old vs New Pattern

### Old Pattern (Convert2CrvUSD.vy)
❌ Requires 2 transactions:
1. `token.approve(converter, amount)`
2. `converter.deposit(token, amount)`

❌ Complex multi-user accounting
❌ Risk of accounting bugs with multiple users

### New Pattern (Factory + PersonalConverter)
✅ Only 1 transaction:
1. `token.transfer(my_personal_converter, amount)`

✅ Simple per-user accounting
✅ Each user has isolated contract
✅ Original design goal achieved!

## Contract Addresses

After deployment, you'll find addresses in `deployment_factory.json`:

```json
{
  "factory_address": "0x...",
  "blueprint_address": "0x...",
  "deployed_at": "2024-..."
}
```

## Testing

Run comprehensive factory tests:

```bash
pytest tests/test_factory.py -v
```

Key test scenarios:
- Factory deployment
- Personal converter deployment
- Direct token transfers (no approve!)
- Order creation and settlement
- Order cancellation and expiry
- Refund mechanism
- Multi-user independence

## Security Considerations

1. **Owner Control**: Each personal converter is controlled by its owner
   - Only owner can emergency withdraw
   - Only operator can create orders (trusted role)

2. **Order Safety**:
   - Orders have expiration timestamps
   - Anyone can cancel expired orders
   - Operator can cancel active orders

3. **Refund Mechanism**:
   - Non-whitelisted tokens can be refunded to owner
   - 5% fee: 4% to fee collector, 1% to initiator

4. **Blueprint Security**:
   - Blueprint cannot be upgraded
   - Each personal converter is independent
   - Factory cannot access user funds

## Gas Costs

Approximate gas costs on Arbitrum:

- Deploy Blueprint: ~500k gas (one-time)
- Deploy Factory: ~1.5M gas (one-time)
- Deploy Personal Converter: ~60k gas per user
- Create Order: ~150k gas
- Settle Order: ~100k gas

## Operator Role

The operator is a trusted role responsible for:
1. Monitoring user personal converters for token deposits
2. Creating CoW orders with favorable pricing
3. Marking orders as settled after execution
4. Cancelling orders if needed

The operator pays gas fees for order creation and settlement.

## Future Enhancements

Potential improvements:
1. **Off-chain monitoring service** to automatically detect deposits and create orders
2. **Batched order creation** for multiple users
3. **Custom slippage parameters** per user
4. **Automated order retry** on failure
5. **Integration with CoW Hooks** for advanced order types

## Support

For issues or questions:
- GitHub Issues: [Link]
- Documentation: This file
- Tests: `tests/test_factory.py`
