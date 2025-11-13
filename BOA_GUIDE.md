# Boa Interaction Guide

Complete guide for interacting with the deployed Convert2CrvUSD contract using Titanoboa.

## 🚀 Quick Start

### Prerequisites

```bash
# Install dependencies
./install.sh
source .venv/bin/activate

# Configure .env_arbitrum with:
# - ARBITRUM_RPC_URL
# - PRIVATE_KEY
# - Contract addresses
```

### Interactive Mode

```bash
# Start interactive menu
python scripts/boa_interact.py

# Run examples
python scripts/boa_examples.py
```

## 📖 Usage Guide

### 1. View Contract Information

```python
from scripts.boa_interact import Convert2CrvUSDInteractor

# Initialize
interactor = Convert2CrvUSDInteractor()

# Get contract info
interactor.get_contract_info()

# Check whitelisted tokens
tokens = interactor.get_whitelisted_tokens()

# Check if token is whitelisted
is_whitelisted = interactor.is_token_whitelisted("0x...")
```

### 2. User Operations

#### Deposit Tokens

```python
# Approve and deposit WETH
weth_address = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"
amount = 1 * 10**18  # 1 WETH

# Option 1: Separate approve and deposit
interactor.approve_token(weth_address, amount)
interactor.deposit(weth_address, amount)

# Option 2: Combined
interactor.approve_and_deposit(weth_address, amount)
```

#### Check Balance

```python
# Check your deposited balance
balance = interactor.get_user_balance(
    interactor.account.address,
    weth_address
)
print(f"Deposited: {balance / 10**18} WETH")
```

#### Refund Non-Whitelisted Token

```python
# Refund non-whitelisted token (5% fee)
interactor.refund_non_whitelisted_token(
    user_address="0x...",
    token_address="0x..."
)
```

### 3. Operator Operations

#### Create Order

```python
import time

# Create order to sell user's WETH for crvUSD
order_uid = interactor.create_order(
    user="0x...",  # User whose tokens to sell
    sell_token="0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",  # WETH
    sell_amount=1 * 10**18,  # 1 WETH
    min_buy_amount=2000 * 10**18,  # Min 2000 crvUSD
    valid_to=int(time.time()) + 3600  # Valid for 1 hour
)

print(f"Order UID: {order_uid.hex()}")
```

#### Settle Order

```python
# After CoW solver fills the order
interactor.settle_order(
    order_uid=order_uid,
    crv_usd_received=2100 * 10**18  # Amount user received
)
```

#### Cancel Order

```python
# Cancel before expiry (operator only)
interactor.cancel_order(order_uid)

# Cancel after expiry (anyone can call)
interactor.cancel_expired_order(order_uid)
```

#### Get Order Details

```python
order_info = interactor.get_active_order(order_uid)
print(f"User: {order_info['user']}")
print(f"Sell Amount: {order_info['sell_amount']}")
print(f"Is Active: {order_info['is_active']}")
```

### 4. Owner Operations

#### Manage Whitelist

```python
# Add token to whitelist
interactor.add_whitelisted_token("0x...")

# Remove token from whitelist
interactor.remove_whitelisted_token("0x...")
```

#### Update Configuration

```python
# Set new operator
interactor.set_operator("0x...")

# Set new fee collector
interactor.set_fee_collector("0x...")

# Transfer ownership (careful!)
interactor.transfer_ownership("0x...")
```

#### Emergency Withdraw

```python
# Emergency withdrawal (owner only)
interactor.emergency_withdraw_token(
    token="0x...",
    amount=1000 * 10**18
)
```

## 🔄 Common Workflows

### Complete User Journey

```python
# 1. User deposits WETH
interactor.approve_and_deposit(
    token=WETH,
    amount=10 * 10**18
)

# 2. Operator creates order
order_uid = interactor.create_order(
    user=user_address,
    sell_token=WETH,
    sell_amount=10 * 10**18,
    min_buy_amount=20000 * 10**18,
    valid_to=int(time.time()) + 3600
)

# 3. CoW solver fills order (happens off-chain)
# User receives crvUSD directly from CoW settlement

# 4. Operator marks as settled
interactor.settle_order(
    order_uid=order_uid,
    crv_usd_received=21000 * 10**18
)
```

### Monitor Active Orders

```python
# Get order from transaction or event
order_uid = bytes.fromhex("...")

# Check order status
order = interactor.get_active_order(order_uid)

if order['is_active']:
    print("Order still active")
    if order['expiry'] < int(time.time()):
        print("Order expired, can cancel")
        interactor.cancel_expired_order(order_uid)
else:
    print("Order settled or cancelled")
```

### Batch Operations

```python
# Check balances for multiple tokens
tokens = interactor.get_whitelisted_tokens()

for token in tokens:
    balance = interactor.get_user_balance(
        user_address,
        token
    )
    print(f"{token}: {balance}")
```

## 🛠️ Programmatic Usage

### As Python Module

```python
from scripts.boa_interact import Convert2CrvUSDInteractor

# Initialize with specific address
interactor = Convert2CrvUSDInteractor(
    contract_address="0x..."
)

# Use anywhere in your code
interactor.deposit(token, amount)
```

### Custom Scripts

```python
# my_script.py
from scripts.boa_interact import Convert2CrvUSDInteractor
import time

def auto_create_orders():
    """Automatically create orders for all deposits"""
    interactor = Convert2CrvUSDInteractor()

    users = ["0x...", "0x..."]  # List of users
    tokens = interactor.get_whitelisted_tokens()

    for user in users:
        for token in tokens:
            balance = interactor.get_user_balance(user, token)

            if balance > 0:
                # Create order
                order_uid = interactor.create_order(
                    user=user,
                    sell_token=token,
                    sell_amount=balance,
                    min_buy_amount=calculate_min_buy(token, balance),
                    valid_to=int(time.time()) + 3600
                )
                print(f"Created order {order_uid.hex()} for {user}")

if __name__ == "__main__":
    auto_create_orders()
```

## 🔍 Debugging

### Enable Verbose Logging

```python
import boa
boa.env.evm.patch.logger.setLevel("DEBUG")
```

### Check Transaction Details

```python
# Boa will show transaction details
try:
    interactor.deposit(token, amount)
except Exception as e:
    print(f"Transaction failed: {e}")
    # Check gas, approvals, balances
```

### Simulate Before Executing

```python
# Use boa's simulation features
with boa.env.anchor():
    # Try operation
    interactor.deposit(token, amount)
    # Reverts automatically if simulation
```

## 📝 Token Addresses (Arbitrum)

```python
# Mainnet addresses
WETH = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"
USDC = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
CRV = "0x11cDb42B0EB46D95f990BeDD4695A6e3fA034978"
CRV_USD = "0x498Bf2B1e120FeD3ad3D42EA2165E9b73f99C1e5"

# CoW Protocol
COW_SETTLEMENT = "0x9008D19f58AAbD9eD0D60971565AA8510560ab41"
```

## 🔒 Security Notes

- Never commit `.env_arbitrum` with real private keys
- Use separate operator account (not owner)
- Test on testnet first (Arbitrum Sepolia)
- Verify all transactions before signing
- Keep private keys secure

## 🆘 Troubleshooting

### "ARBITRUM_RPC_URL not found"
- Edit `.env_arbitrum` with your Alchemy key

### "Insufficient allowance"
- Call `approve_token()` before `deposit()`

### "Only operator" error
- Check you're using the operator account
- Or update operator with owner account

### "Token not whitelisted"
- Only WETH, USDC, CRV accepted by default
- Owner can add more via `add_whitelisted_token()`

### Connection issues
- Check Alchemy RPC URL is correct
- Verify you have API credits
- Try different RPC if needed

## 📚 Resources

- [Boa Documentation](https://github.com/vyperlang/titanoboa)
- [CoW Protocol Docs](https://docs.cow.fi/)
- [Arbitrum Docs](https://docs.arbitrum.io/)
- Contract source: `contracts/Convert2CrvUSD.vy`
