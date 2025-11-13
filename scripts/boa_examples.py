"""
Example usage of boa_interact.py
Shows common operations with the Convert2CrvUSD contract
"""
import time
from boa_interact import Convert2CrvUSDInteractor


def example_user_flow():
    """Example: User deposits WETH and gets it converted to crvUSD"""
    print("\n" + "=" * 60)
    print("Example 1: User Deposit and Conversion Flow")
    print("=" * 60)

    # Initialize interactor
    interactor = Convert2CrvUSDInteractor()

    # Check contract info
    interactor.get_contract_info()

    # Check if WETH is whitelisted
    print("\n📋 Checking if WETH is whitelisted...")
    interactor.is_token_whitelisted(interactor.WETH)

    # Deposit WETH
    weth_amount = 1 * 10**18  # 1 WETH
    print(f"\n💰 Depositing {weth_amount / 10**18} WETH...")

    # Approve and deposit
    interactor.approve_and_deposit(interactor.WETH, weth_amount)

    # Check balance
    print("\n📊 Checking deposited balance...")
    interactor.get_user_balance(interactor.account.address, interactor.WETH)

    print("\n✅ Deposit complete! Operator will now create an order.")


def example_operator_create_order():
    """Example: Operator creates order for user"""
    print("\n" + "=" * 60)
    print("Example 2: Operator Creates Order")
    print("=" * 60)

    interactor = Convert2CrvUSDInteractor()

    # Order parameters
    user = interactor.account.address  # Or specific user
    sell_token = interactor.WETH
    sell_amount = 1 * 10**18  # 1 WETH
    min_buy_amount = 2000 * 10**18  # Minimum 2000 crvUSD
    valid_to = int(time.time()) + 3600  # Valid for 1 hour

    # Create order
    order_uid = interactor.create_order(
        user=user,
        sell_token=sell_token,
        sell_amount=sell_amount,
        min_buy_amount=min_buy_amount,
        valid_to=valid_to
    )

    # Get order details
    interactor.get_active_order(order_uid)

    print("\n✅ Order created! Now wait for CoW solvers to fill it.")
    print(f"📝 Order UID: {order_uid.hex()}")


def example_settle_order():
    """Example: Operator settles a filled order"""
    print("\n" + "=" * 60)
    print("Example 3: Settle Order After CoW Execution")
    print("=" * 60)

    interactor = Convert2CrvUSDInteractor()

    # Get order UID from previous example
    order_uid_hex = input("Enter order UID (from create_order): ").strip()
    if order_uid_hex.startswith("0x"):
        order_uid_hex = order_uid_hex[2:]

    order_uid = bytes.fromhex(order_uid_hex)

    # Amount of crvUSD the user received (check on-chain)
    crv_usd_received = int(input("Enter crvUSD received: ").strip())

    # Settle the order
    interactor.settle_order(order_uid, crv_usd_received)

    print("\n✅ Order settled! User has received their crvUSD directly.")


def example_refund_non_whitelisted():
    """Example: Refund non-whitelisted token"""
    print("\n" + "=" * 60)
    print("Example 4: Refund Non-Whitelisted Token")
    print("=" * 60)

    interactor = Convert2CrvUSDInteractor()

    # User who deposited non-whitelisted token
    user = input("Enter user address: ").strip()
    token = input("Enter non-whitelisted token address: ").strip()

    # Check balance
    balance = interactor.get_user_balance(user, token)

    if balance == 0:
        print("❌ No balance to refund")
        return

    # Calculate fees
    total_fee = balance * 500 // 10000  # 5%
    fee_to_collector = balance * 400 // 10000  # 4%
    fee_to_initiator = balance * 100 // 10000  # 1%
    amount_to_user = balance - total_fee

    print(f"\n💸 Refund Breakdown:")
    print(f"  Total Balance: {balance}")
    print(f"  To User (95%): {amount_to_user}")
    print(f"  To Fee Collector (4%): {fee_to_collector}")
    print(f"  To You (1%): {fee_to_initiator}")

    # Initiate refund
    interactor.refund_non_whitelisted_token(user, token)

    print("\n✅ Refund complete!")


def example_check_balances():
    """Example: Check various balances"""
    print("\n" + "=" * 60)
    print("Example 5: Check Balances")
    print("=" * 60)

    interactor = Convert2CrvUSDInteractor()

    user = interactor.account.address

    # Check all whitelisted tokens
    tokens = interactor.get_whitelisted_tokens()

    print(f"\n📊 Balances for {user}:")
    for token in tokens:
        balance = interactor.get_user_balance(user, token)
        # Would need to get token symbol for better display
        print(f"  Token {token}: {balance}")


def example_owner_operations():
    """Example: Owner operations"""
    print("\n" + "=" * 60)
    print("Example 6: Owner Operations")
    print("=" * 60)

    interactor = Convert2CrvUSDInteractor()

    print("\n📋 Current Configuration:")
    interactor.get_contract_info()

    print("\n⚙️  Owner Operations Menu:")
    print("  1. Add new whitelisted token")
    print("  2. Remove whitelisted token")
    print("  3. Update operator")
    print("  4. Update fee collector")

    choice = input("\nEnter choice (or 0 to skip): ").strip()

    if choice == "1":
        token = input("Enter token address to whitelist: ").strip()
        interactor.add_whitelisted_token(token)

    elif choice == "2":
        token = input("Enter token address to remove: ").strip()
        interactor.remove_whitelisted_token(token)

    elif choice == "3":
        operator = input("Enter new operator address: ").strip()
        interactor.set_operator(operator)

    elif choice == "4":
        fee_collector = input("Enter new fee collector address: ").strip()
        interactor.set_fee_collector(fee_collector)


def main():
    """Main menu for examples"""
    print("\n" + "=" * 60)
    print("Convert2CrvUSD - Boa Examples")
    print("=" * 60)

    while True:
        print("\n📚 Available Examples:")
        print("  1. User deposit and conversion flow")
        print("  2. Operator creates order")
        print("  3. Settle order after execution")
        print("  4. Refund non-whitelisted token")
        print("  5. Check balances")
        print("  6. Owner operations")
        print("\n  0. Exit")

        choice = input("\nEnter choice: ").strip()

        try:
            if choice == "0":
                print("\n👋 Goodbye!")
                break
            elif choice == "1":
                example_user_flow()
            elif choice == "2":
                example_operator_create_order()
            elif choice == "3":
                example_settle_order()
            elif choice == "4":
                example_refund_non_whitelisted()
            elif choice == "5":
                example_check_balances()
            elif choice == "6":
                example_owner_operations()
            else:
                print("❌ Invalid choice")

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
