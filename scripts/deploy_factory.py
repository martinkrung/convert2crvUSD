"""
Deployment script for ConverterFactory and PersonalConverter blueprint on Arbitrum
Uses Alchemy RPC and loads configuration from .env_arbitrum
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import boa
from eth_account import Account
from web3 import Web3


# Load environment variables
env_path = Path(__file__).parent.parent / ".env_arbitrum"
load_dotenv(env_path)


def validate_environment():
    """Validate all required environment variables are set"""
    required_vars = [
        "ARBITRUM_RPC_URL",
        "PRIVATE_KEY",
        "FEE_COLLECTOR",
        "COWSWAP_SETTLEMENT",
        "CRV_USD",
        "WETH",
        "USDC",
        "CRV"
    ]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please edit .env_arbitrum with the required values")
        sys.exit(1)

    print("✅ All required environment variables found")


def setup_network():
    """Set up connection to Arbitrum network"""
    rpc_url = os.getenv("ARBITRUM_RPC_URL")
    print(f"🌐 Connecting to Arbitrum via {rpc_url[:50]}...")

    # Set up Web3 provider
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        print("❌ Failed to connect to Arbitrum RPC")
        sys.exit(1)

    # Get chain ID to confirm network
    chain_id = w3.eth.chain_id
    if chain_id == 42161:
        print("✅ Connected to Arbitrum One (Mainnet)")
    elif chain_id == 421614:
        print("✅ Connected to Arbitrum Sepolia (Testnet)")
    else:
        print(f"⚠️  Connected to unknown network (Chain ID: {chain_id})")

    return w3


def load_deployer_account():
    """Load deployer account from private key"""
    private_key = os.getenv("PRIVATE_KEY")

    if private_key.startswith("0x"):
        private_key = private_key[2:]

    try:
        account = Account.from_key(private_key)
        print(f"👤 Deployer address: {account.address}")
        return account
    except Exception as e:
        print(f"❌ Failed to load private key: {e}")
        sys.exit(1)


def check_deployer_balance(w3, account):
    """Check deployer has sufficient ETH for deployment"""
    balance = w3.eth.get_balance(account.address)
    balance_eth = w3.from_wei(balance, 'ether')

    print(f"💰 Deployer balance: {balance_eth:.4f} ETH")

    if balance < w3.to_wei(0.01, 'ether'):
        print("⚠️  Warning: Balance is low. Deployment may fail due to insufficient gas.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(0)


def deploy_blueprint(account):
    """Deploy the PersonalConverter blueprint"""
    print("\n📘 Deploying PersonalConverter blueprint...")

    try:
        # Load contract
        contract_path = Path(__file__).parent.parent / "contracts" / "PersonalConverter.vy"

        print("🔨 Compiling PersonalConverter...")
        blueprint = boa.load_partial(str(contract_path)).deploy_as_blueprint()

        print(f"✅ Blueprint deployed at: {blueprint}")
        return blueprint

    except Exception as e:
        print(f"\n❌ Blueprint deployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def deploy_factory(w3, account, blueprint_address):
    """Deploy the ConverterFactory contract"""
    print("\n🏭 Deploying ConverterFactory contract...")

    # Get deployment parameters from env
    admin = account.address
    operator = os.getenv("OPERATOR", account.address)  # Default to deployer if not set
    fee_collector = os.getenv("FEE_COLLECTOR")
    cow_settlement = os.getenv("COWSWAP_SETTLEMENT")
    crv_usd = os.getenv("CRV_USD")

    # Initial whitelist
    weth = os.getenv("WETH")
    usdc = os.getenv("USDC")
    crv = os.getenv("CRV")
    initial_whitelist = [weth, usdc, crv]

    print(f"\nDeployment parameters:")
    print(f"  Admin: {admin}")
    print(f"  Operator: {operator}")
    print(f"  Fee Collector: {fee_collector}")
    print(f"  CoW Settlement: {cow_settlement}")
    print(f"  crvUSD: {crv_usd}")
    print(f"  Blueprint: {blueprint_address}")
    print(f"  Initial Whitelist: {initial_whitelist}")

    # Confirm deployment
    response = input("\nProceed with factory deployment? (y/n): ")
    if response.lower() != 'y':
        print("Deployment cancelled")
        sys.exit(0)

    try:
        # Load and deploy factory
        factory_path = Path(__file__).parent.parent / "contracts" / "ConverterFactory.vy"

        print("\n🔨 Compiling factory...")
        factory = boa.load(
            str(factory_path),
            admin,
            operator,
            fee_collector,
            cow_settlement,
            crv_usd,
            blueprint_address,
            initial_whitelist
        )

        print(f"\n✅ Factory deployed at: {factory.address}")

        # Save deployment info
        save_deployment_info(
            factory.address,
            blueprint_address,
            account.address,
            initial_whitelist
        )

        return factory

    except Exception as e:
        print(f"\n❌ Factory deployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def save_deployment_info(factory_address, blueprint_address, deployer, whitelist):
    """Save deployment information to file"""
    deployment_file = Path(__file__).parent.parent / "deployment_factory.json"

    import json
    from datetime import datetime

    deployment_info = {
        "factory_address": factory_address,
        "blueprint_address": blueprint_address,
        "deployer": deployer,
        "deployed_at": datetime.now().isoformat(),
        "network": "arbitrum",
        "cow_settlement": os.getenv("COWSWAP_SETTLEMENT"),
        "crv_usd": os.getenv("CRV_USD"),
        "whitelisted_tokens": {
            "WETH": os.getenv("WETH"),
            "USDC": os.getenv("USDC"),
            "CRV": os.getenv("CRV")
        }
    }

    with open(deployment_file, 'w') as f:
        json.dump(deployment_info, f, indent=2)

    print(f"\n📄 Deployment info saved to {deployment_file}")


def main():
    """Main deployment function"""
    print("=" * 70)
    print("ConverterFactory + PersonalConverter Blueprint Deployment")
    print("=" * 70)

    # Validate environment
    validate_environment()

    # Setup network
    w3 = setup_network()

    # Load deployer account
    account = load_deployer_account()

    # Check balance
    check_deployer_balance(w3, account)

    # Set up boa with web3 provider
    boa.set_network_env(os.getenv("ARBITRUM_RPC_URL"))
    boa.env.add_account(account, force_eoa=True)

    # Deploy blueprint
    blueprint_address = deploy_blueprint(account)

    # Deploy factory
    factory = deploy_factory(w3, account, blueprint_address)

    print("\n" + "=" * 70)
    print("✅ Deployment Complete!")
    print("=" * 70)
    print(f"\nBlueprint Address: {blueprint_address}")
    print(f"Factory Address: {factory.address}")
    print("\nNext steps:")
    print("1. Verify contracts on Arbiscan")
    print("2. Users can deploy personal converters via factory.deploy_personal_converter(user_address)")
    print("3. Users send tokens directly to their personal converter address")
    print("4. Operator creates orders for users")
    print("\nKey Feature: Users can send tokens directly without approve()!")


if __name__ == "__main__":
    main()
