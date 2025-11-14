# Convert2CrvUSD

A Vyper smart contract system on Arbitrum that accepts various tokens and automatically converts them to crvUSD via CoW Swap.

## 🎯 Overview

This project implements a **factory pattern** that achieves the original design goal:

**Users can send tokens directly to a contract without `approve()`!**

### How It Works

1. **Factory deploys personal converter** for each user (cheap via blueprint pattern)
2. **User sends tokens directly** to their personal converter (no approve needed!)
3. **Operator creates CoW orders** on behalf of the user
4. **User receives crvUSD directly** from CoW settlement

See [FACTORY_PATTERN.md](./FACTORY_PATTERN.md) for detailed architecture.

## ✨ Key Features

- **No Approve Required**: Users just send tokens directly (1 transaction vs 2!)
- **Factory Pattern**: Each user gets their own personal converter contract
- **Blueprint Deployment**: Cheap per-user deployment (~60k gas)
- **Direct Settlement**: Users receive crvUSD directly from CoW Protocol
- **Token Whitelist**: WETH, USDC, and CRV accepted by default
- **CoW Protocol Integration**: Uses ERC-1271 for programmatic order validation
- **Refund Mechanism**: Non-whitelisted tokens refundable with 5% fee
- **Order Timeout Protection**: Expired orders can be cancelled
- **Isolated Balances**: No multi-user accounting complexity
- **Comprehensive Tests**: Full test coverage with Titanoboa
- **Arbitrum Optimized**: Built specifically for Arbitrum network

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     ConverterFactory                     │
│  - Deploys personal converters for users                │
│  - Manages global config (operator, whitelist)          │
└────────────────┬────────────────────────────────────────┘
                 │
                 │ deploys via blueprint
                 │
                 v
┌────────────────────────────────────────────────────────┐
│              PersonalConverter (per user)              │
│  - Fixed owner (the user)                              │
│  - Accepts direct token transfers                      │
│  - Operator creates CoW orders                         │
│  - User receives crvUSD directly                       │
└────────────────────────────────────────────────────────┘
```

## 📋 Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Alchemy API key (for Arbitrum RPC)
- Arbiscan API key (for contract verification)

## 🚀 Installation

```bash
# Clone the repository
git clone <repository-url>
cd convert2crvUSD

# Run installation script
chmod +x install.sh
./install.sh

# Activate virtual environment
source .venv/bin/activate

# Edit configuration
nano .env_arbitrum
```

### Environment Configuration

Edit `.env_arbitrum` with your settings:

```bash
# Arbitrum RPC
ARBITRUM_RPC_URL=https://arb-mainnet.g.alchemy.com/v2/YOUR_KEY

# Deployment
PRIVATE_KEY=your_private_key_here
FEE_COLLECTOR=your_fee_collector_address

# Contract Addresses (Arbitrum Mainnet - pre-filled)
COWSWAP_SETTLEMENT=0x9008D19f58AAbD9eD0D60971565AA8510560ab41
COMPOSABLE_COW=0xfdaFc9d1902f4e0b84f65F49f244b32b31013b74
CRV_USD=0x498Bf2B1e120FeD3ad3D42EA2165E9b73f99C1e5
WETH=0x82aF49447D8a07e3bd95BD0d56f35241523fBab1
USDC=0xaf88d065e77c8cC2239327C5EDb3A432268e5831
CRV=0x11cDb42B0EB46D95f990BeDD4695A6e3fA034978

# Verification
ARBISCAN_API_KEY=your_arbiscan_key
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run factory pattern tests
pytest tests/test_factory.py -v

# Run legacy pattern tests
pytest tests/test_deposit.py tests/test_orders.py -v

# Run with coverage
pytest tests/ --cov=contracts --cov-report=html
```

### Test Coverage

- ✅ Factory deployment and personal converter creation
- ✅ Direct token transfers (no approve!)
- ✅ Order creation and settlement
- ✅ Order cancellation and timeouts
- ✅ Refund mechanism with fees
- ✅ Multi-user independence
- ✅ Access control
- ✅ Edge cases and security

## 📦 Deployment

### Option 1: Factory Pattern (Recommended)

```bash
python scripts/deploy_factory.py
```

This will:
1. Deploy PersonalConverter blueprint
2. Deploy ConverterFactory
3. Initialize with whitelisted tokens (WETH, USDC, CRV)
4. Save deployment info to `deployment_factory.json`

**Advantages**:
- Users can send tokens directly (no approve!)
- Each user gets their own contract
- Simple accounting, no multi-user complexity

### Option 2: Legacy Pattern

```bash
python scripts/deploy.py
```

This will:
- Deploy single Convert2CrvUSD contract
- Requires users to approve + deposit
- Uses internal balance tracking

**Note**: Factory pattern is recommended for production use.

### 2. Verify on Arbiscan

```bash
python scripts/verify.py
```

This will:
- Load deployment information
- Create verification guide
- Attempt API verification (may require manual verification)

**Note**: Vyper contracts often require manual verification on Arbiscan. See `VERIFICATION_GUIDE.md` for instructions.

### 3. Interact with Deployed Contract

```bash
# Interactive mode with Titanoboa
python scripts/boa_interact.py

# Or run examples
python scripts/boa_examples.py
```

Features:
- ✅ Full contract interaction via Titanoboa
- ✅ No ABIs needed - uses Vyper source directly
- ✅ Interactive CLI menu
- ✅ Programmatic usage support
- ✅ Works with deployed contracts on-chain

See [BOA_GUIDE.md](BOA_GUIDE.md) for complete documentation.

## 🏗️ Architecture

### Smart Contract: Convert2CrvUSD.vy

#### Core Components

1. **User Deposits**
   - Users deposit tokens via `deposit(token, amount)`
   - Internal balance tracking: `user_token_balance[user][token]`
   - No withdrawal function needed (crvUSD sent directly)

2. **Token Whitelist**
   - Configurable list of accepted tokens
   - Owner can add/remove tokens
   - Non-whitelisted tokens can be refunded with fees

3. **CoW Protocol Integration**
   - Orders created via `create_order()`
   - ERC-1271 signature validation
   - Pre-signature pattern for gas efficiency
   - **Receiver is the user** - they get crvUSD directly

4. **Order Lifecycle**
   ```
   Deposit → Create Order → CoW Solver Fills → User Receives crvUSD
        ↓         ↓
   [Timeout] → Cancel → User Keeps Tokens
   ```

5. **Fee System**
   - Refund fee: 500 bps (5%)
   - Fee collector: 400 bps (4%)
   - Refund initiator: 100 bps (1%)

### Key Contracts (Arbitrum)

| Contract | Address |
|----------|---------|
| GPv2Settlement | `0x9008D19f58AAbD9eD0D60971565AA8510560ab41` |
| ComposableCoW | `0xfdaFc9d1902f4e0b84f65F49f244b32b31013b74` |
| crvUSD | `0x498Bf2B1e120FeD3ad3D42EA2165E9b73f99C1e5` |
| WETH | `0x82aF49447D8a07e3bd95BD0d56f35241523fBab1` |
| USDC | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` |
| CRV | `0x11cDb42B0EB46D95f990BeDD4695A6e3fA034978` |

## 📖 Usage

### For Users

1. **Deposit Tokens**
   ```python
   # Approve contract
   token.approve(converter_address, amount)

   # Deposit
   converter.deposit(token_address, amount)
   ```

2. **Wait for Order**
   - Operator creates order on your behalf
   - CoW solver finds best price and executes
   - You receive crvUSD directly to your wallet

3. **Refund Non-Whitelisted Token** (optional)
   ```python
   converter.refund_non_whitelisted_token(your_address, token_address)
   ```

### For Operators

1. **Create Order**
   ```python
   order_uid = converter.create_order(
       user=user_address,
       sell_token=token_address,
       sell_amount=amount,
       min_buy_amount=minimum_crvusd,
       valid_to=expiry_timestamp,
       app_data=metadata
   )
   ```

2. **Monitor Settlement**
   - Watch for CoW Protocol settlement events
   - Call `settle_order(order_uid, crv_usd_received)` after settlement

3. **Cancel Expired Orders**
   ```python
   converter.cancel_order(order_uid)  # Before expiry
   converter.cancel_expired_order(order_uid)  # After expiry (anyone can call)
   ```

### For Contract Owners

1. **Manage Whitelist**
   ```python
   converter.add_whitelisted_token(token_address)
   converter.remove_whitelisted_token(token_address)
   ```

2. **Update Roles**
   ```python
   converter.set_operator(new_operator)
   converter.set_fee_collector(new_collector)
   converter.transfer_ownership(new_owner)
   ```

## 🔒 Security Features

- ✅ Reentrancy protection via checks-effects-interactions pattern
- ✅ Access control (owner, operator roles)
- ✅ Order validation via ERC-1271
- ✅ Timeout protection for unfilled orders
- ✅ Per-user balance tracking
- ✅ Emergency withdrawal function
- ✅ No direct ETH acceptance

## 🛠️ Development

### Project Structure

```
convert2crvUSD/
├── contracts/
│   └── Convert2CrvUSD.vy      # Main contract
├── interfaces/
│   ├── IERC20.vyi              # ERC20 interface
│   ├── IGPv2Settlement.vyi     # CoW settlement
│   └── IERC1271.vyi            # Signature validation
├── scripts/
│   ├── deploy.py               # Deployment script
│   └── verify.py               # Verification script
├── tests/
│   ├── conftest.py             # Test fixtures
│   ├── test_deposit.py         # Deposit tests
│   ├── test_whitelist.py       # Whitelist tests
│   ├── test_orders.py          # Order tests
│   ├── test_refunds.py         # Refund tests
│   └── test_access_control.py  # Access control tests
├── pyproject.toml              # Python dependencies
├── install.sh                  # Installation script
├── .env_arbitrum               # Environment config
└── README.md                   # This file
```

### Variable Naming Convention

All variables use `snake_case` following Vyper and CoW Protocol conventions:

- `user_token_balance` - User balances
- `whitelisted_tokens` - Token whitelist
- `cow_settlement` - CoW Protocol contracts
- `order_uid` - Order identifiers
- `fee_collector` - Fee recipient

## 📚 Resources

- [CoW Protocol Documentation](https://docs.cow.fi/)
- [Vyper Documentation](https://docs.vyperlang.org/)
- [Titanoboa Testing Framework](https://github.com/vyperlang/titanoboa)
- [Arbitrum Documentation](https://docs.arbitrum.io/)

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## ⚠️ Disclaimer

This software is provided "as is" without warranty. Use at your own risk. Always audit smart contracts before deploying to mainnet.

## 📄 License

[Specify your license here]

## 🙏 Acknowledgments

- CoW Protocol team for the DEX aggregation infrastructure
- Curve Finance for crvUSD
- Vyper community for the excellent smart contract language
- Arbitrum for the L2 scaling solution
