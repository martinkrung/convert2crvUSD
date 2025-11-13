"""
Boa script to interact with deployed Convert2CrvUSD contract on Arbitrum
Supports all contract operations: deposits, orders, refunds, admin functions
"""
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import boa
from eth_account import Account


# Load environment variables
env_path = Path(__file__).parent.parent / ".env_arbitrum"
load_dotenv(env_path)


class Convert2CrvUSDInteractor:
    """
    Interact with Convert2CrvUSD contract using Titanoboa
    """

    def __init__(self, contract_address: str = None):
        """
        Initialize the interactor

        Args:
            contract_address: Address of deployed contract (or load from deployment.json)
        """
        self.setup_network()
        self.load_account()

        if contract_address:
            self.contract_address = contract_address
        else:
            self.contract_address = self.load_deployment_address()

        self.load_contract()
        self.load_token_addresses()

    def setup_network(self):
        """Setup connection to Arbitrum"""
        rpc_url = os.getenv("ARBITRUM_RPC_URL")
        if not rpc_url:
            print("❌ ARBITRUM_RPC_URL not found in .env_arbitrum")
            sys.exit(1)

        print(f"🌐 Connecting to Arbitrum...")
        boa.set_network_env(rpc_url)
        print(f"✅ Connected to Arbitrum")

    def load_account(self):
        """Load account from private key"""
        private_key = os.getenv("PRIVATE_KEY")
        if not private_key:
            print("❌ PRIVATE_KEY not found in .env_arbitrum")
            sys.exit(1)

        if private_key.startswith("0x"):
            private_key = private_key[2:]

        self.account = Account.from_key(private_key)
        boa.env.add_account(self.account, force_eoa=True)
        print(f"👤 Loaded account: {self.account.address}")

    def load_deployment_address(self):
        """Load contract address from deployment.json"""
        deployment_file = Path(__file__).parent.parent / "deployment.json"

        if not deployment_file.exists():
            print("❌ deployment.json not found. Please deploy contract first or provide address.")
            sys.exit(1)

        with open(deployment_file, 'r') as f:
            deployment_info = json.load(f)

        return deployment_info['contract_address']

    def load_contract(self):
        """Load the deployed contract"""
        print(f"📜 Loading contract at {self.contract_address}...")

        # Load contract from source
        contract_path = Path(__file__).parent.parent / "contracts" / "Convert2CrvUSD.vy"

        # Use boa.load_partial to load at specific address
        self.contract = boa.load_partial(str(contract_path)).at(self.contract_address)

        print(f"✅ Contract loaded")

    def load_token_addresses(self):
        """Load token addresses from env"""
        self.WETH = os.getenv("WETH", "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1")
        self.USDC = os.getenv("USDC", "0xaf88d065e77c8cC2239327C5EDb3A432268e5831")
        self.CRV = os.getenv("CRV", "0x11cDb42B0EB46D95f990BeDD4695A6e3fA034978")
        self.CRV_USD = os.getenv("CRV_USD", "0x498Bf2B1e120FeD3ad3D42EA2165E9b73f99C1e5")

    # ========== VIEW FUNCTIONS ==========

    def get_user_balance(self, user: str, token: str) -> int:
        """Get user's deposited balance"""
        balance = self.contract.get_user_balance(user, token)
        print(f"Balance: {balance}")
        return balance

    def get_whitelisted_tokens(self):
        """Get all whitelisted tokens"""
        tokens = self.contract.get_whitelisted_tokens()
        print("\n📋 Whitelisted Tokens:")
        for i, token in enumerate(tokens, 1):
            print(f"  {i}. {token}")
        return tokens

    def is_token_whitelisted(self, token: str) -> bool:
        """Check if token is whitelisted"""
        is_whitelisted = self.contract.is_token_whitelisted(token)
        status = "✅ Whitelisted" if is_whitelisted else "❌ Not whitelisted"
        print(f"{status}")
        return is_whitelisted

    def get_contract_info(self):
        """Get contract configuration"""
        print("\n📊 Contract Information:")
        print(f"  Address: {self.contract_address}")
        print(f"  Owner: {self.contract.owner()}")
        print(f"  Operator: {self.contract.operator()}")
        print(f"  Fee Collector: {self.contract.fee_collector()}")
        print(f"  CoW Settlement: {self.contract.cow_settlement()}")
        print(f"  CoW Vault Relayer: {self.contract.cow_vault_relayer()}")
        print(f"  crvUSD Token: {self.contract.crv_usd_token()}")

    def get_active_order(self, order_uid: bytes) -> dict:
        """Get active order details"""
        order = self.contract.active_orders(order_uid)
        order_info = {
            "order_hash": order[0],
            "order_uid": order[1],
            "user": order[2],
            "sell_token": order[3],
            "sell_amount": order[4],
            "expiry": order[5],
            "is_active": order[6]
        }
        print("\n📦 Order Details:")
        for key, value in order_info.items():
            print(f"  {key}: {value}")
        return order_info

    # ========== USER FUNCTIONS ==========

    def approve_token(self, token: str, amount: int):
        """
        Approve contract to spend tokens

        Args:
            token: Token address
            amount: Amount to approve
        """
        print(f"\n💰 Approving {amount} tokens...")

        # Load ERC20 contract
        erc20_abi = """
# @version 0.4.3
@external
def approve(spender: address, amount: uint256) -> bool:
    pass
        """
        token_contract = boa.loads(erc20_abi, name="ERC20").at(token)

        # Approve
        token_contract.approve(self.contract_address, amount)
        print(f"✅ Approval successful")

    def deposit(self, token: str, amount: int):
        """
        Deposit tokens

        Args:
            token: Token address
            amount: Amount to deposit
        """
        print(f"\n📥 Depositing {amount} tokens...")

        # First approve if not already approved
        print("Note: Make sure you've approved the contract first!")

        # Deposit
        self.contract.deposit(token, amount)
        print(f"✅ Deposit successful")

    def approve_and_deposit(self, token: str, amount: int):
        """
        Approve and deposit in one go

        Args:
            token: Token address
            amount: Amount to deposit
        """
        self.approve_token(token, amount)
        self.deposit(token, amount)

    def refund_non_whitelisted_token(self, user: str, token: str):
        """
        Refund non-whitelisted tokens (takes 5% fee)

        Args:
            user: User address
            token: Token address
        """
        print(f"\n💸 Refunding non-whitelisted token...")
        print(f"  User: {user}")
        print(f"  Token: {token}")
        print(f"  ⚠️  5% fee will be deducted (4% to fee collector, 1% to you)")

        self.contract.refund_non_whitelisted_token(user, token)
        print(f"✅ Refund successful")

    # ========== OPERATOR FUNCTIONS ==========

    def create_order(
        self,
        user: str,
        sell_token: str,
        sell_amount: int,
        min_buy_amount: int,
        valid_to: int,
        app_data: bytes = b"\x00" * 32
    ) -> bytes:
        """
        Create CoW Protocol order (operator only)

        Args:
            user: User whose tokens to sell
            sell_token: Token to sell
            sell_amount: Amount to sell
            min_buy_amount: Minimum crvUSD to receive
            valid_to: Order expiry timestamp
            app_data: Application-specific data

        Returns:
            order_uid: Order unique identifier
        """
        print(f"\n📋 Creating order...")
        print(f"  User: {user}")
        print(f"  Sell Token: {sell_token}")
        print(f"  Sell Amount: {sell_amount}")
        print(f"  Min Buy Amount: {min_buy_amount}")
        print(f"  Valid To: {valid_to}")

        order_uid = self.contract.create_order(
            user,
            sell_token,
            sell_amount,
            min_buy_amount,
            valid_to,
            app_data
        )

        print(f"✅ Order created")
        print(f"  Order UID: {order_uid.hex()}")
        return order_uid

    def settle_order(self, order_uid: bytes, crv_usd_received: int):
        """
        Mark order as settled (operator only)

        Args:
            order_uid: Order identifier
            crv_usd_received: Amount of crvUSD user received
        """
        print(f"\n✅ Settling order...")
        print(f"  Order UID: {order_uid.hex()}")
        print(f"  crvUSD Received: {crv_usd_received}")

        self.contract.settle_order(order_uid, crv_usd_received)
        print(f"✅ Order settled")

    def cancel_order(self, order_uid: bytes):
        """
        Cancel active order (operator only)

        Args:
            order_uid: Order identifier
        """
        print(f"\n❌ Cancelling order...")
        print(f"  Order UID: {order_uid.hex()}")

        self.contract.cancel_order(order_uid)
        print(f"✅ Order cancelled")

    def cancel_expired_order(self, order_uid: bytes):
        """
        Cancel expired order (anyone can call)

        Args:
            order_uid: Order identifier
        """
        print(f"\n⏰ Cancelling expired order...")
        print(f"  Order UID: {order_uid.hex()}")

        self.contract.cancel_expired_order(order_uid)
        print(f"✅ Expired order cancelled")

    # ========== OWNER FUNCTIONS ==========

    def add_whitelisted_token(self, token: str):
        """Add token to whitelist (owner only)"""
        print(f"\n➕ Adding token to whitelist...")
        print(f"  Token: {token}")

        self.contract.add_whitelisted_token(token)
        print(f"✅ Token added to whitelist")

    def remove_whitelisted_token(self, token: str):
        """Remove token from whitelist (owner only)"""
        print(f"\n➖ Removing token from whitelist...")
        print(f"  Token: {token}")

        self.contract.remove_whitelisted_token(token)
        print(f"✅ Token removed from whitelist")

    def set_operator(self, new_operator: str):
        """Set operator address (owner only)"""
        print(f"\n🔧 Setting operator...")
        print(f"  New Operator: {new_operator}")

        self.contract.set_operator(new_operator)
        print(f"✅ Operator updated")

    def set_fee_collector(self, new_fee_collector: str):
        """Set fee collector address (owner only)"""
        print(f"\n🔧 Setting fee collector...")
        print(f"  New Fee Collector: {new_fee_collector}")

        self.contract.set_fee_collector(new_fee_collector)
        print(f"✅ Fee collector updated")

    def transfer_ownership(self, new_owner: str):
        """Transfer ownership (owner only)"""
        print(f"\n👑 Transferring ownership...")
        print(f"  New Owner: {new_owner}")
        print(f"  ⚠️  This action is irreversible!")

        confirm = input("Type 'CONFIRM' to proceed: ")
        if confirm != "CONFIRM":
            print("❌ Transfer cancelled")
            return

        self.contract.transfer_ownership(new_owner)
        print(f"✅ Ownership transferred")

    def emergency_withdraw_token(self, token: str, amount: int):
        """Emergency withdraw tokens (owner only)"""
        print(f"\n🚨 Emergency withdrawal...")
        print(f"  Token: {token}")
        print(f"  Amount: {amount}")
        print(f"  ⚠️  This is for emergency use only!")

        confirm = input("Type 'EMERGENCY' to proceed: ")
        if confirm != "EMERGENCY":
            print("❌ Withdrawal cancelled")
            return

        self.contract.emergency_withdraw_token(token, amount)
        print(f"✅ Emergency withdrawal complete")


def interactive_menu():
    """Interactive CLI menu"""
    print("=" * 60)
    print("Convert2CrvUSD - Boa Interaction Script")
    print("=" * 60)

    # Initialize
    interactor = Convert2CrvUSDInteractor()

    while True:
        print("\n" + "=" * 60)
        print("Main Menu")
        print("=" * 60)
        print("\n📊 View Functions:")
        print("  1. Get contract info")
        print("  2. Get whitelisted tokens")
        print("  3. Check token whitelist status")
        print("  4. Check user balance")
        print("  5. Get active order details")

        print("\n👤 User Functions:")
        print("  6. Approve token")
        print("  7. Deposit token")
        print("  8. Approve and deposit")
        print("  9. Refund non-whitelisted token")

        print("\n🔧 Operator Functions:")
        print("  10. Create order")
        print("  11. Settle order")
        print("  12. Cancel order")
        print("  13. Cancel expired order")

        print("\n👑 Owner Functions:")
        print("  14. Add whitelisted token")
        print("  15. Remove whitelisted token")
        print("  16. Set operator")
        print("  17. Set fee collector")
        print("  18. Transfer ownership")
        print("  19. Emergency withdraw")

        print("\n  0. Exit")

        choice = input("\nEnter choice: ").strip()

        try:
            if choice == "0":
                print("\n👋 Goodbye!")
                break

            elif choice == "1":
                interactor.get_contract_info()

            elif choice == "2":
                interactor.get_whitelisted_tokens()

            elif choice == "3":
                token = input("Token address: ").strip()
                interactor.is_token_whitelisted(token)

            elif choice == "4":
                user = input("User address (press Enter for your address): ").strip()
                if not user:
                    user = interactor.account.address
                token = input("Token address: ").strip()
                interactor.get_user_balance(user, token)

            elif choice == "5":
                order_uid = input("Order UID (hex): ").strip()
                if order_uid.startswith("0x"):
                    order_uid = order_uid[2:]
                interactor.get_active_order(bytes.fromhex(order_uid))

            elif choice == "6":
                token = input("Token address: ").strip()
                amount = int(input("Amount: ").strip())
                interactor.approve_token(token, amount)

            elif choice == "7":
                token = input("Token address: ").strip()
                amount = int(input("Amount: ").strip())
                interactor.deposit(token, amount)

            elif choice == "8":
                token = input("Token address: ").strip()
                amount = int(input("Amount: ").strip())
                interactor.approve_and_deposit(token, amount)

            elif choice == "9":
                user = input("User address: ").strip()
                token = input("Token address: ").strip()
                interactor.refund_non_whitelisted_token(user, token)

            elif choice == "10":
                user = input("User address: ").strip()
                token = input("Sell token address: ").strip()
                sell_amount = int(input("Sell amount: ").strip())
                min_buy = int(input("Min crvUSD to receive: ").strip())
                valid_to = int(input("Valid to (timestamp): ").strip())
                interactor.create_order(user, token, sell_amount, min_buy, valid_to)

            elif choice == "11":
                order_uid = input("Order UID (hex): ").strip()
                if order_uid.startswith("0x"):
                    order_uid = order_uid[2:]
                crv_usd = int(input("crvUSD received: ").strip())
                interactor.settle_order(bytes.fromhex(order_uid), crv_usd)

            elif choice == "12":
                order_uid = input("Order UID (hex): ").strip()
                if order_uid.startswith("0x"):
                    order_uid = order_uid[2:]
                interactor.cancel_order(bytes.fromhex(order_uid))

            elif choice == "13":
                order_uid = input("Order UID (hex): ").strip()
                if order_uid.startswith("0x"):
                    order_uid = order_uid[2:]
                interactor.cancel_expired_order(bytes.fromhex(order_uid))

            elif choice == "14":
                token = input("Token address: ").strip()
                interactor.add_whitelisted_token(token)

            elif choice == "15":
                token = input("Token address: ").strip()
                interactor.remove_whitelisted_token(token)

            elif choice == "16":
                operator = input("New operator address: ").strip()
                interactor.set_operator(operator)

            elif choice == "17":
                fee_collector = input("New fee collector address: ").strip()
                interactor.set_fee_collector(fee_collector)

            elif choice == "18":
                new_owner = input("New owner address: ").strip()
                interactor.transfer_ownership(new_owner)

            elif choice == "19":
                token = input("Token address: ").strip()
                amount = int(input("Amount: ").strip())
                interactor.emergency_withdraw_token(token, amount)

            else:
                print("❌ Invalid choice")

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("""
Usage: python scripts/boa_interact.py [options]

Options:
  --help              Show this help message
  (no args)           Start interactive menu

Example Usage:
  # Interactive mode
  python scripts/boa_interact.py

  # Programmatic usage
  from scripts.boa_interact import Convert2CrvUSDInteractor

  interactor = Convert2CrvUSDInteractor()
  interactor.get_contract_info()
  interactor.deposit(token_address, amount)
        """)
    else:
        interactive_menu()
