"""
Tests for CoW Protocol order creation and management
"""
import pytest
import boa


def test_create_order(converter, operator, weth, crv_usd, funded_alice):
    """Test creating a CoW order"""
    deposit_amount = 10 * 10**18
    sell_amount = 5 * 10**18
    min_buy_amount = 5000 * 10**18  # Minimum crvUSD

    # Alice deposits WETH
    with boa.env.prank(funded_alice):
        weth.approve(converter.address, deposit_amount)
        converter.deposit(weth.address, deposit_amount)

    # Operator creates order
    valid_to = boa.env.vm.state.timestamp + 3600  # 1 hour
    app_data = b"\x00" * 32

    with boa.env.prank(operator):
        order_uid = converter.create_order(
            funded_alice,
            weth.address,
            sell_amount,
            min_buy_amount,
            valid_to,
            app_data
        )

    # Verify order was created
    assert order_uid != b"\x00" * 32

    # Check order details
    order = converter.active_orders(order_uid)
    assert order[2] == funded_alice  # user
    assert order[3] == weth.address  # sell_token
    assert order[4] == sell_amount  # sell_amount
    assert order[6] == True  # is_active


def test_create_order_non_operator_fails(converter, alice, weth, funded_alice):
    """Test non-operator cannot create orders"""
    deposit_amount = 10 * 10**18
    sell_amount = 5 * 10**18

    with boa.env.prank(funded_alice):
        weth.approve(converter.address, deposit_amount)
        converter.deposit(weth.address, deposit_amount)

    valid_to = boa.env.vm.state.timestamp + 3600
    app_data = b"\x00" * 32

    with boa.env.prank(alice):
        with boa.reverts("Only operator"):
            converter.create_order(
                funded_alice,
                weth.address,
                sell_amount,
                1000 * 10**18,
                valid_to,
                app_data
            )


def test_create_order_non_whitelisted_token_fails(converter, operator, random_token, funded_bob):
    """Test creating order for non-whitelisted token fails"""
    deposit_amount = 100 * 10**18

    with boa.env.prank(funded_bob):
        random_token.approve(converter.address, deposit_amount)
        converter.deposit(random_token.address, deposit_amount)

    valid_to = boa.env.vm.state.timestamp + 3600
    app_data = b"\x00" * 32

    with boa.env.prank(operator):
        with boa.reverts("Token not whitelisted"):
            converter.create_order(
                funded_bob,
                random_token.address,
                deposit_amount,
                1000 * 10**18,
                valid_to,
                app_data
            )


def test_create_order_insufficient_balance_fails(converter, operator, weth, funded_alice):
    """Test creating order with insufficient balance fails"""
    deposit_amount = 5 * 10**18
    sell_amount = 10 * 10**18  # More than deposited

    with boa.env.prank(funded_alice):
        weth.approve(converter.address, deposit_amount)
        converter.deposit(weth.address, deposit_amount)

    valid_to = boa.env.vm.state.timestamp + 3600
    app_data = b"\x00" * 32

    with boa.env.prank(operator):
        with boa.reverts("Insufficient balance"):
            converter.create_order(
                funded_alice,
                weth.address,
                sell_amount,
                1000 * 10**18,
                valid_to,
                app_data
            )


def test_create_order_expired_timestamp_fails(converter, operator, weth, funded_alice):
    """Test creating order with past timestamp fails"""
    deposit_amount = 10 * 10**18

    with boa.env.prank(funded_alice):
        weth.approve(converter.address, deposit_amount)
        converter.deposit(weth.address, deposit_amount)

    valid_to = boa.env.vm.state.timestamp - 1  # Past timestamp
    app_data = b"\x00" * 32

    with boa.env.prank(operator):
        with boa.reverts("Already expired"):
            converter.create_order(
                funded_alice,
                weth.address,
                deposit_amount,
                1000 * 10**18,
                valid_to,
                app_data
            )


def test_settle_order(converter, operator, weth, crv_usd, funded_alice):
    """Test settling a CoW order"""
    deposit_amount = 10 * 10**18
    sell_amount = 5 * 10**18

    # Alice deposits
    with boa.env.prank(funded_alice):
        weth.approve(converter.address, deposit_amount)
        converter.deposit(weth.address, deposit_amount)

    # Create order
    valid_to = boa.env.vm.state.timestamp + 3600
    app_data = b"\x00" * 32

    # Check balance before order
    initial_balance = converter.get_user_balance(funded_alice, weth.address)
    assert initial_balance == deposit_amount

    with boa.env.prank(operator):
        order_uid = converter.create_order(
            funded_alice,
            weth.address,
            sell_amount,
            1000 * 10**18,
            valid_to,
            app_data
        )

        # Balance should be deducted immediately when order is created
        balance_after_create = converter.get_user_balance(funded_alice, weth.address)
        assert balance_after_create == initial_balance - sell_amount

        # Simulate settlement - in reality CoW solver would fill this
        # Settle with amount of crvUSD received (simulated)
        crv_usd_amount = 2000 * 10**18
        converter.settle_order(order_uid, crv_usd_amount)

        # Balance should remain the same (already deducted)
        final_balance = converter.get_user_balance(funded_alice, weth.address)
        assert final_balance == balance_after_create

        # Check order is no longer active
        order = converter.active_orders(order_uid)
        assert order[6] == False  # is_active


def test_cancel_order(converter, operator, weth, funded_alice):
    """Test cancelling an active order"""
    deposit_amount = 10 * 10**18
    sell_amount = 5 * 10**18

    with boa.env.prank(funded_alice):
        weth.approve(converter.address, deposit_amount)
        converter.deposit(weth.address, deposit_amount)

    valid_to = boa.env.vm.state.timestamp + 3600
    app_data = b"\x00" * 32

    with boa.env.prank(operator):
        order_uid = converter.create_order(
            funded_alice,
            weth.address,
            sell_amount,
            1000 * 10**18,
            valid_to,
            app_data
        )

        # Balance deducted when order created
        balance_after_create = converter.get_user_balance(funded_alice, weth.address)
        assert balance_after_create == deposit_amount - sell_amount

        # Cancel order
        converter.cancel_order(order_uid)

        # Check order is inactive
        order = converter.active_orders(order_uid)
        assert order[6] == False

        # Balance should be refunded back to user
        balance = converter.get_user_balance(funded_alice, weth.address)
        assert balance == deposit_amount


def test_cancel_expired_order(converter, operator, weth, funded_alice):
    """Test cancelling an expired order"""
    deposit_amount = 10 * 10**18
    sell_amount = 5 * 10**18

    with boa.env.prank(funded_alice):
        weth.approve(converter.address, deposit_amount)
        converter.deposit(weth.address, deposit_amount)

    valid_to = boa.env.vm.state.timestamp + 100
    app_data = b"\x00" * 32

    with boa.env.prank(operator):
        order_uid = converter.create_order(
            funded_alice,
            weth.address,
            sell_amount,
            1000 * 10**18,
            valid_to,
            app_data
        )

    # Balance deducted when order created
    balance_after_create = converter.get_user_balance(funded_alice, weth.address)
    assert balance_after_create == deposit_amount - sell_amount

    # Advance time past expiry
    boa.env.time_travel(seconds=200)

    # Anyone can cancel expired order
    with boa.env.prank(funded_alice):
        converter.cancel_expired_order(order_uid)

    # Check order is inactive
    order = converter.active_orders(order_uid)
    assert order[6] == False

    # Balance should be refunded back to user
    final_balance = converter.get_user_balance(funded_alice, weth.address)
    assert final_balance == deposit_amount


def test_cancel_non_expired_order_fails(converter, operator, weth, funded_alice, alice):
    """Test cancelling non-expired order by non-operator fails"""
    deposit_amount = 10 * 10**18
    sell_amount = 5 * 10**18

    with boa.env.prank(funded_alice):
        weth.approve(converter.address, deposit_amount)
        converter.deposit(weth.address, deposit_amount)

    valid_to = boa.env.vm.state.timestamp + 3600
    app_data = b"\x00" * 32

    with boa.env.prank(operator):
        order_uid = converter.create_order(
            funded_alice,
            weth.address,
            sell_amount,
            1000 * 10**18,
            valid_to,
            app_data
        )

    # Non-operator tries to cancel before expiry
    with boa.env.prank(alice):
        with boa.reverts("Order not expired"):
            converter.cancel_expired_order(order_uid)


def test_erc1271_signature_validation(converter):
    """Test ERC-1271 signature validation"""
    message_hash = b"\x00" * 32
    signature = b"\x00" * 100

    # Should return magic value
    result = converter.isValidSignature(message_hash, signature)
    assert result == b"\x16\x26\xba\x7e"  # ERC1271_MAGIC_VALUE
