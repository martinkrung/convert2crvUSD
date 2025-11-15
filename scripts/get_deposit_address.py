"""
Example: How to get your personal converter address and send tokens

This script demonstrates the complete user flow:
1. Query factory for your converter address
2. Deploy a personal converter if you don't have one
3. Send tokens directly to your converter address
4. Check your balance
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import boa
from eth_account import Account

# Load environment
env_path = Path(__file__).parent.parent / ".env_arbitrum"
load_dotenv(env_path)


def main():
    # Setup
    rpc_url = os.getenv("ARBITRUM_RPC_URL")
    boa.set_network_env(rpc_url)

    # Load user account
    private_key = os.getenv("PRIVATE_KEY")
    if private_key.startswith("0x"):
        private_key = private_key[2:]
    user = Account.from_key(private_key)
    boa.env.add_account(user, force_eoa=True)

    print(f"User address: {user.address}")
    print()

    # Load factory (you need to deploy it first and set the address)
    FACTORY_ADDRESS = os.getenv("FACTORY_ADDRESS")
    if not FACTORY_ADDRESS:
        print("Error: Please deploy the factory first and set FACTORY_ADDRESS in .env_arbitrum")
        return

    factory = boa.load_partial("contracts/ConverterFactory.vy").at(FACTORY_ADDRESS)

    print("=" * 60)
    print("STEP 1: Query your personal converter address")
    print("=" * 60)

    # Method 1: Simple address query
    my_converter = factory.get_deposit_address(user.address)
    print(f"\nMethod 1 - get_deposit_address():")
    print(f"  Your converter: {my_converter}")

    # Method 2: Comprehensive info
    has_converter, converter_addr = factory.get_converter_info(user.address)
    print(f"\nMethod 2 - get_converter_info():")
    print(f"  Has converter: {has_converter}")
    print(f"  Converter address: {converter_addr}")

    # Method 3: Boolean check
    has_it = factory.has_converter(user.address)
    print(f"\nMethod 3 - has_converter():")
    print(f"  Has converter: {has_it}")

    print()
    print("=" * 60)
    print("STEP 2: Deploy personal converter if needed")
    print("=" * 60)

    if my_converter == "0x0000000000000000000000000000000000000000":
        print("\nYou don't have a converter yet. Deploying...")

        # Deploy personal converter
        # Note: Anyone can call this, not just the user
        my_converter = factory.deploy_personal_converter(user.address)

        print(f"✅ Personal converter deployed at: {my_converter}")
        print(f"   Gas used: ~60,000")
    else:
        print(f"\n✅ You already have a converter at: {my_converter}")

    print()
    print("=" * 60)
    print("STEP 3: Send tokens to your converter")
    print("=" * 60)

    print(f"\nYour personal converter address: {my_converter}")
    print("\nTo send tokens (example with WETH):")
    print()
    print("  # Get WETH contract")
    print("  weth = boa.load_partial('interfaces/IERC20.vyi').at(WETH_ADDRESS)")
    print()
    print("  # Send WETH directly to your converter (NO APPROVE NEEDED!)")
    print(f"  weth.transfer('{my_converter}', 5 * 10**18)  # 5 WETH")
    print()
    print("  That's it! Just 1 transaction. No approve() needed!")

    print()
    print("=" * 60)
    print("STEP 4: Check what tokens you can convert")
    print("=" * 60)

    whitelisted = factory.get_whitelisted_tokens()
    print(f"\nWhitelisted tokens ({len(whitelisted)}):")
    for i, token in enumerate(whitelisted, 1):
        print(f"  {i}. {token}")

    print()
    print("=" * 60)
    print("COMPLETE FLOW SUMMARY")
    print("=" * 60)
    print()
    print("As a user, you only need to:")
    print()
    print(f"1. Get your converter address:")
    print(f"   → factory.get_deposit_address('{user.address}')")
    print(f"   → Result: {my_converter}")
    print()
    print("2. Send tokens directly to that address:")
    print(f"   → weth.transfer('{my_converter}', amount)")
    print("   → NO approve() needed! Just one transaction!")
    print()
    print("3. Wait for operator to create CoW order")
    print()
    print("4. Receive crvUSD directly in your wallet!")
    print()
    print("=" * 60)

    # Bonus: Check converter balance
    print()
    print("BONUS: Check your converter's balance")
    print("=" * 60)

    converter = boa.load_partial("contracts/PersonalConverter.vy").at(my_converter)

    print(f"\nYour converter: {my_converter}")
    print(f"Owner: {converter.owner()}")

    # Check available balance for WETH
    WETH_ADDRESS = os.getenv("WETH")
    if WETH_ADDRESS:
        weth_balance = converter.get_available_balance(WETH_ADDRESS)
        print(f"\nWETH available balance: {weth_balance / 10**18:.4f} WETH")

    # Check if there's an active order
    active_order = converter.active_order()
    is_active = active_order[5]  # is_active field
    if is_active:
        print(f"\n⏳ Active order exists")
        print(f"   Sell token: {active_order[2]}")
        print(f"   Sell amount: {active_order[3]}")
    else:
        print(f"\n✅ No active orders")


if __name__ == "__main__":
    main()
