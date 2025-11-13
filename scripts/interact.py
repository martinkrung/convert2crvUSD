"""
Helper script to interact with deployed Convert2CrvUSD contract
"""
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account


# Load environment
env_path = Path(__file__).parent.parent / ".env_arbitrum"
load_dotenv(env_path)


def load_deployment():
    """Load deployment information"""
    deployment_file = Path(__file__).parent.parent / "deployment.json"
    if not deployment_file.exists():
        print("❌ deployment.json not found. Run deploy.py first.")
        sys.exit(1)

    with open(deployment_file, 'r') as f:
        return json.load(f)


def setup_web3():
    """Setup Web3 connection"""
    rpc_url = os.getenv("ARBITRUM_RPC_URL")
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        print("❌ Failed to connect to Arbitrum")
        sys.exit(1)

    return w3


def load_contract_abi():
    """Load or create minimal ABI for interaction"""
    # Minimal ABI for common interactions
    return [
        {
            "name": "deposit",
            "type": "function",
            "stateMutability": "nonpayable",
            "inputs": [
                {"name": "token", "type": "address"},
                {"name": "amount", "type": "uint256"}
            ],
            "outputs": []
        },
        {
            "name": "get_user_balance",
            "type": "function",
            "stateMutability": "view",
            "inputs": [
                {"name": "user", "type": "address"},
                {"name": "token", "type": "address"}
            ],
            "outputs": [{"name": "", "type": "uint256"}]
        },
        {
            "name": "is_token_whitelisted",
            "type": "function",
            "stateMutability": "view",
            "inputs": [{"name": "token", "type": "address"}],
            "outputs": [{"name": "", "type": "bool"}]
        },
        {
            "name": "get_whitelisted_tokens",
            "type": "function",
            "stateMutability": "view",
            "inputs": [],
            "outputs": [{"name": "", "type": "address[]"}]
        },
        {
            "name": "refund_non_whitelisted_token",
            "type": "function",
            "stateMutability": "nonpayable",
            "inputs": [
                {"name": "user", "type": "address"},
                {"name": "token", "type": "address"}
            ],
            "outputs": []
        }
    ]


def check_balance(w3, contract, user_address, token_address):
    """Check user's deposited balance"""
    try:
        balance = contract.functions.get_user_balance(
            user_address,
            token_address
        ).call()

        print(f"Balance: {Web3.from_wei(balance, 'ether')} tokens")
        return balance
    except Exception as e:
        print(f"❌ Error checking balance: {e}")
        return 0


def check_whitelisted_tokens(contract):
    """Display whitelisted tokens"""
    try:
        tokens = contract.functions.get_whitelisted_tokens().call()

        print("\n📋 Whitelisted Tokens:")
        for i, token in enumerate(tokens, 1):
            print(f"  {i}. {token}")

        return tokens
    except Exception as e:
        print(f"❌ Error getting whitelisted tokens: {e}")
        return []


def deposit_tokens(w3, contract, token_address, amount):
    """Deposit tokens to the contract"""
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        print("❌ PRIVATE_KEY not found in .env_arbitrum")
        return

    account = Account.from_key(private_key)

    # Build transaction
    try:
        tx = contract.functions.deposit(
            token_address,
            amount
        ).build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gas': 200000,
            'gasPrice': w3.eth.gas_price
        })

        # Sign and send
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        print(f"📤 Transaction sent: {tx_hash.hex()}")
        print("⏳ Waiting for confirmation...")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        if receipt['status'] == 1:
            print("✅ Deposit successful!")
        else:
            print("❌ Transaction failed")

        return receipt

    except Exception as e:
        print(f"❌ Error depositing: {e}")
        return None


def interactive_menu(w3, contract, deployment_info):
    """Interactive menu for contract operations"""
    while True:
        print("\n" + "=" * 60)
        print("Convert2CrvUSD - Interactive Menu")
        print("=" * 60)
        print(f"Contract: {deployment_info['contract_address']}")
        print(f"Network: Arbitrum (Chain ID: {w3.eth.chain_id})")
        print("\nOptions:")
        print("1. Check whitelisted tokens")
        print("2. Check your balance")
        print("3. Deposit tokens (requires token approval first)")
        print("4. Check token whitelist status")
        print("5. Exit")

        choice = input("\nEnter choice (1-5): ").strip()

        if choice == "1":
            check_whitelisted_tokens(contract)

        elif choice == "2":
            user = input("Enter user address (or press Enter for your address): ").strip()
            if not user:
                private_key = os.getenv("PRIVATE_KEY")
                if private_key:
                    user = Account.from_key(private_key).address
                else:
                    print("❌ No PRIVATE_KEY in .env_arbitrum")
                    continue

            token = input("Enter token address: ").strip()
            check_balance(w3, contract, user, token)

        elif choice == "3":
            token = input("Enter token address: ").strip()
            amount_str = input("Enter amount (in wei): ").strip()
            try:
                amount = int(amount_str)
                print("\n⚠️  Make sure you have approved the contract to spend your tokens!")
                confirm = input("Continue? (y/n): ")
                if confirm.lower() == 'y':
                    deposit_tokens(w3, contract, token, amount)
            except ValueError:
                print("❌ Invalid amount")

        elif choice == "4":
            token = input("Enter token address: ").strip()
            try:
                is_whitelisted = contract.functions.is_token_whitelisted(token).call()
                status = "✅ Whitelisted" if is_whitelisted else "❌ Not whitelisted"
                print(f"\n{status}")
            except Exception as e:
                print(f"❌ Error: {e}")

        elif choice == "5":
            print("\n👋 Goodbye!")
            break

        else:
            print("❌ Invalid choice")


def main():
    """Main function"""
    print("=" * 60)
    print("Convert2CrvUSD - Contract Interaction Script")
    print("=" * 60)

    # Setup
    deployment_info = load_deployment()
    w3 = setup_web3()

    print(f"✅ Connected to Arbitrum (Chain ID: {w3.eth.chain_id})")

    # Load contract
    contract_address = Web3.to_checksum_address(deployment_info['contract_address'])
    abi = load_contract_abi()
    contract = w3.eth.contract(address=contract_address, abi=abi)

    print(f"✅ Loaded contract at {contract_address}")

    # Run interactive menu
    interactive_menu(w3, contract, deployment_info)


if __name__ == "__main__":
    main()
