#!/bin/bash
set -e

echo "🚀 Installing convert2crvUSD project dependencies..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

echo "✅ uv is installed"

# Create virtual environment and install dependencies
echo "📦 Creating virtual environment and installing dependencies..."
uv venv
source .venv/bin/activate
uv pip install -e .

echo "📄 Creating .env_arbitrum template..."
if [ ! -f .env_arbitrum ]; then
    cat > .env_arbitrum << 'EOF'
# Arbitrum Configuration
ARBITRUM_RPC_URL=https://arb-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_KEY
ARBITRUM_SEPOLIA_RPC_URL=https://arb-sepolia.g.alchemy.com/v2/YOUR_ALCHEMY_KEY

# Deployment Account
PRIVATE_KEY=your_private_key_here

# Contract Addresses (Arbitrum Mainnet)
COWSWAP_SETTLEMENT=0x9008D19f58AAbD9eD0D60971565AA8510560ab41
COMPOSABLE_COW=0xfdaFc9d1902f4e0b84f65F49f244b32b31013b74

# Token Addresses (Arbitrum)
WETH=0x82aF49447D8a07e3bd95BD0d56f35241523fBab1
USDC=0xaf88d065e77c8cC2239327C5EDb3A432268e5831
CRV=0x11cDb42B0EB46D95f990BeDD4695A6e3fA034978
CRV_USD=0x498Bf2B1e120FeD3ad3D42EA2165E9b73f99C1e5

# Etherscan API Key for verification
ARBISCAN_API_KEY=your_arbiscan_api_key_here

# Fee Collector Address
FEE_COLLECTOR=your_fee_collector_address_here
EOF
    echo "⚠️  Please edit .env_arbitrum with your actual values"
else
    echo "✅ .env_arbitrum already exists"
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env_arbitrum with your Alchemy API key and other settings"
echo "2. Activate the virtual environment: source .venv/bin/activate"
echo "3. Run tests: pytest tests/"
echo "4. Deploy: python scripts/deploy.py"
