# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### 1. Install Dependencies

```bash
./install.sh
source .venv/bin/activate
```

### 2. Configure Environment

Edit `.env_arbitrum`:

```bash
# Required
ARBITRUM_RPC_URL=https://arb-mainnet.g.alchemy.com/v2/YOUR_KEY
PRIVATE_KEY=your_private_key
FEE_COLLECTOR=your_fee_collector_address

# Optional - pre-filled with Arbitrum mainnet addresses
ARBISCAN_API_KEY=your_key_for_verification
```

### 3. Run Tests

```bash
pytest tests/ -v
```

### 4. Deploy to Arbitrum

```bash
python scripts/deploy.py
```

### 5. Verify Contract

```bash
python scripts/verify.py
```

## 📝 Key Concepts

### For Users

1. **Deposit**: Send whitelisted tokens (WETH, USDC, CRV) to contract
2. **Auto-Convert**: Operator creates order via CoW Protocol
3. **Receive**: Get crvUSD directly to your wallet (no withdrawal needed!)

### For Operators

1. **Monitor**: Watch for user deposits
2. **Create Orders**: Call `create_order()` for pending deposits
3. **Track**: Monitor CoW Protocol for settlement
4. **Settle**: Call `settle_order()` after settlement

### Flow Diagram

```
User                Contract             CoW Protocol         User
  |                     |                      |               |
  |--deposit WETH------>|                      |               |
  |                     |                      |               |
  |                     |<--create order-------|               |
  |                     |                      |               |
  |                     |---order params------>|               |
  |                     |                      |               |
  |                     |                   [Solver]           |
  |                     |                   finds best         |
  |                     |                   price              |
  |                     |                      |               |
  |                     |<--execute order------|               |
  |                     |                      |               |
  |                     |                   crvUSD------------>|
  |                     |                   sent directly      |
  |                     |                      |               |
  |                     |<--mark settled-------|               |
  |                     |                      |               |
```

## 🔑 Important Addresses (Arbitrum)

```python
# Your deployed contract
CONTRACT = "See deployment.json after deploy"

# CoW Protocol
SETTLEMENT = "0x9008D19f58AAbD9eD0D60971565AA8510560ab41"

# Tokens
crvUSD = "0x498Bf2B1e120FeD3ad3D42EA2165E9b73f99C1e5"
WETH = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"
USDC = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
CRV = "0x11cDb42B0EB46D95f990BeDD4695A6e3fA034978"
```

## 💡 Common Operations

### Deposit Tokens

```python
# Using Web3.py
from web3 import Web3

w3 = Web3(Web3.HTTPProvider(rpc_url))
contract = w3.eth.contract(address=contract_address, abi=abi)

# Approve first
token.functions.approve(contract_address, amount).transact()

# Then deposit
contract.functions.deposit(token_address, amount).transact()
```

### Check Balance

```python
balance = contract.functions.get_user_balance(
    user_address,
    token_address
).call()
```

### Create Order (Operator)

```python
order_uid = contract.functions.create_order(
    user=user_address,
    sell_token=weth_address,
    sell_amount=10 * 10**18,  # 10 WETH
    min_buy_amount=20000 * 10**18,  # Min 20k crvUSD
    valid_to=int(time.time()) + 3600,  # 1 hour
    app_data=b"\\x00" * 32
).transact()
```

## 🛠️ Troubleshooting

### "Transfer failed" error
- Ensure token approval before deposit
- Check you have sufficient token balance

### "Token not whitelisted" error
- Only WETH, USDC, CRV are whitelisted by default
- Owner can add more via `add_whitelisted_token()`

### "Order not expired" error
- Wait for order expiry before calling `cancel_expired_order()`
- Or have operator call `cancel_order()` before expiry

### Gas too high
- Orders are created off-chain via CoW API
- Only deposit and settlement require gas

## 📚 Next Steps

- Read [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- Check [README.md](README.md) for complete documentation
- Review tests in `tests/` for usage examples
- Join CoW Protocol Discord for support

## ⚡ Pro Tips

1. **Batch deposits**: Save gas by depositing larger amounts less frequently
2. **Monitor orders**: Use CoW Protocol API to track order status
3. **Set realistic minimums**: `min_buy_amount` too high = order won't fill
4. **Use app_data**: Include metadata for tracking/analytics
5. **Emergency functions**: Owner can emergency withdraw if needed

## 🔗 Resources

- [CoW Protocol Docs](https://docs.cow.fi/)
- [CoW Protocol API](https://api.cow.fi/docs/)
- [Arbitrum Explorer](https://arbiscan.io/)
- [Vyper Docs](https://docs.vyperlang.org/)
