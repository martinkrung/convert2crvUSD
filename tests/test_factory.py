"""
Tests for the ConverterFactory and PersonalConverter pattern
"""
import pytest
import boa


def test_factory_deployment(factory, owner, operator, fee_collector, settlement, crv_usd):
    """Test factory deploys correctly"""
    assert factory.admin() == owner
    assert factory.operator() == operator
    assert factory.fee_collector() == fee_collector
    assert factory.cow_settlement() == settlement.address
    assert factory.crv_usd_token() == crv_usd.address
    assert factory.deployment_count() == 0


def test_factory_initial_whitelist(factory, weth, usdc, crv):
    """Test factory initializes with whitelisted tokens"""
    assert factory.is_token_whitelisted(weth.address)
    assert factory.is_token_whitelisted(usdc.address)
    assert factory.is_token_whitelisted(crv.address)

    whitelist = factory.get_whitelisted_tokens()
    assert len(whitelist) == 3
    assert weth.address in whitelist
    assert usdc.address in whitelist
    assert crv.address in whitelist


def test_deploy_personal_converter(factory, alice):
    """Test deploying a personal converter for a user"""
    # Deploy converter for Alice
    converter_addr = factory.deploy_personal_converter(alice)

    assert converter_addr != "0x0000000000000000000000000000000000000000"
    assert factory.get_user_converter(alice) == converter_addr
    assert factory.has_converter(alice) is True
    assert factory.deployment_count() == 1

    # Load the deployed converter
    converter = boa.load_partial("contracts/PersonalConverter.vy").at(converter_addr)
    assert converter.owner() == alice


def test_deploy_personal_converter_idempotent(factory, alice):
    """Test deploying converter twice returns same address"""
    converter1 = factory.deploy_personal_converter(alice)
    converter2 = factory.deploy_personal_converter(alice)

    assert converter1 == converter2
    assert factory.deployment_count() == 1  # Only one deployment


def test_multiple_user_deployments(factory, alice, bob):
    """Test deploying converters for multiple users"""
    alice_converter = factory.deploy_personal_converter(alice)
    bob_converter = factory.deploy_personal_converter(bob)

    assert alice_converter != bob_converter
    assert factory.deployment_count() == 2
    assert factory.get_user_converter(alice) == alice_converter
    assert factory.get_user_converter(bob) == bob_converter


def test_direct_token_transfer_no_approve(alice_converter, alice, weth):
    """Test user can send tokens directly without approve (THE KEY FEATURE!)"""
    # Mint tokens to Alice
    weth.mint(alice, 10 * 10**18)

    # Alice sends tokens DIRECTLY to her converter (no approve!)
    with boa.env.prank(alice):
        weth.transfer(alice_converter.address, 5 * 10**18)

    # Check converter received the tokens
    assert weth.balanceOf(alice_converter.address) == 5 * 10**18
    assert alice_converter.get_available_balance(weth.address) == 5 * 10**18


def test_create_order_from_direct_transfer(alice_converter, alice, weth, operator, crv_usd):
    """Test creating order after direct token transfer"""
    # Alice sends WETH directly to her converter
    weth.mint(alice, 10 * 10**18)
    with boa.env.prank(alice):
        weth.transfer(alice_converter.address, 5 * 10**18)

    # Operator creates order
    sell_amount = 2 * 10**18
    min_buy_amount = 3000 * 10**18  # Expect 3000 crvUSD
    valid_to = boa.env.timestamp + 3600
    app_data = b"\x00" * 32

    with boa.env.prank(operator):
        order_uid = alice_converter.create_order(
            weth.address,
            sell_amount,
            min_buy_amount,
            valid_to,
            app_data
        )

    assert order_uid != b"\x00" * 32

    # Check order is active
    active_order = alice_converter.active_order()
    assert active_order[5] is True  # is_active
    assert active_order[2] == weth.address  # sell_token
    assert active_order[3] == sell_amount  # sell_amount

    # Check available balance reduced (committed to order)
    assert alice_converter.get_available_balance(weth.address) == 3 * 10**18


def test_settle_order(alice_converter, alice, weth, operator, crv_usd):
    """Test settling an order"""
    # Setup: Alice sends WETH, operator creates order
    weth.mint(alice, 10 * 10**18)
    with boa.env.prank(alice):
        weth.transfer(alice_converter.address, 5 * 10**18)

    sell_amount = 2 * 10**18
    min_buy_amount = 3000 * 10**18
    valid_to = boa.env.timestamp + 3600
    app_data = b"\x00" * 32

    with boa.env.prank(operator):
        order_uid = alice_converter.create_order(
            weth.address,
            sell_amount,
            min_buy_amount,
            valid_to,
            app_data
        )

    # Simulate CoW settlement: transfer tokens from converter, send crvUSD to Alice
    vault_relayer = alice_converter.cow_vault_relayer()

    # Vault relayer pulls WETH from converter
    with boa.env.prank(vault_relayer):
        weth.transferFrom(alice_converter.address, vault_relayer, sell_amount)

    # Alice receives crvUSD directly (simulate CoW settlement)
    crv_usd_received = 3100 * 10**18
    crv_usd.mint(alice, crv_usd_received)

    # Operator marks order as settled
    with boa.env.prank(operator):
        alice_converter.settle_order(crv_usd_received)

    # Check order is no longer active
    active_order = alice_converter.active_order()
    assert active_order[5] is False  # is_active

    # Check available balance restored (committed balance released)
    assert alice_converter.get_available_balance(weth.address) == 3 * 10**18

    # Check Alice received crvUSD
    assert crv_usd.balanceOf(alice) == crv_usd_received


def test_cancel_expired_order(alice_converter, alice, weth, operator):
    """Test cancelling an expired order"""
    # Setup: Alice sends WETH, operator creates order
    weth.mint(alice, 10 * 10**18)
    with boa.env.prank(alice):
        weth.transfer(alice_converter.address, 5 * 10**18)

    sell_amount = 2 * 10**18
    min_buy_amount = 3000 * 10**18
    valid_to = boa.env.timestamp + 3600
    app_data = b"\x00" * 32

    with boa.env.prank(operator):
        alice_converter.create_order(
            weth.address,
            sell_amount,
            min_buy_amount,
            valid_to,
            app_data
        )

    # Fast forward past expiry
    boa.env.time_travel(seconds=3601)

    # Anyone can cancel expired order
    alice_converter.cancel_expired_order()

    # Check order is no longer active
    active_order = alice_converter.active_order()
    assert active_order[5] is False

    # Check available balance restored
    assert alice_converter.get_available_balance(weth.address) == 5 * 10**18


def test_operator_cancel_order(alice_converter, alice, weth, operator):
    """Test operator cancelling an active order"""
    # Setup
    weth.mint(alice, 10 * 10**18)
    with boa.env.prank(alice):
        weth.transfer(alice_converter.address, 5 * 10**18)

    sell_amount = 2 * 10**18
    with boa.env.prank(operator):
        alice_converter.create_order(
            weth.address,
            sell_amount,
            3000 * 10**18,
            boa.env.timestamp + 3600,
            b"\x00" * 32
        )

    # Operator cancels order
    with boa.env.prank(operator):
        alice_converter.cancel_order()

    # Check order is inactive and balance restored
    active_order = alice_converter.active_order()
    assert active_order[5] is False
    assert alice_converter.get_available_balance(weth.address) == 5 * 10**18


def test_refund_non_whitelisted_token(alice_converter, alice, random_token, fee_collector):
    """Test refunding non-whitelisted tokens with fees"""
    # Alice accidentally sends non-whitelisted token
    random_token.mint(alice, 1000 * 10**18)
    with boa.env.prank(alice):
        random_token.transfer(alice_converter.address, 1000 * 10**18)

    # Check not whitelisted
    assert not alice_converter.is_token_whitelisted(random_token.address)

    # Anyone can trigger refund
    initiator = boa.env.generate_address("initiator")
    with boa.env.prank(initiator):
        alice_converter.refund_non_whitelisted_token(random_token.address)

    # Check fees: 5% total (4% collector, 1% initiator)
    # 1000 * 0.95 = 950 to Alice
    # 1000 * 0.04 = 40 to collector
    # 1000 * 0.01 = 10 to initiator
    assert random_token.balanceOf(alice) == 950 * 10**18
    assert random_token.balanceOf(fee_collector) == 40 * 10**18
    assert random_token.balanceOf(initiator) == 10 * 10**18


def test_multiple_users_independent_balances(factory, alice, bob, weth):
    """Test multiple users have independent converters and balances"""
    # Deploy converters for both users
    alice_converter_addr = factory.deploy_personal_converter(alice)
    bob_converter_addr = factory.deploy_personal_converter(bob)

    alice_converter = boa.load_partial("contracts/PersonalConverter.vy").at(alice_converter_addr)
    bob_converter = boa.load_partial("contracts/PersonalConverter.vy").at(bob_converter_addr)

    # Both send different amounts
    weth.mint(alice, 10 * 10**18)
    weth.mint(bob, 5 * 10**18)

    with boa.env.prank(alice):
        weth.transfer(alice_converter.address, 10 * 10**18)

    with boa.env.prank(bob):
        weth.transfer(bob_converter.address, 5 * 10**18)

    # Check balances are independent
    assert alice_converter.get_available_balance(weth.address) == 10 * 10**18
    assert bob_converter.get_available_balance(weth.address) == 5 * 10**18


def test_only_operator_can_create_orders(alice_converter, alice, weth):
    """Test that only operator can create orders"""
    weth.mint(alice, 10 * 10**18)
    with boa.env.prank(alice):
        weth.transfer(alice_converter.address, 5 * 10**18)

    # Alice tries to create order (should fail)
    with boa.reverts("Only operator"):
        with boa.env.prank(alice):
            alice_converter.create_order(
                weth.address,
                2 * 10**18,
                3000 * 10**18,
                boa.env.timestamp + 3600,
                b"\x00" * 32
            )


def test_cannot_create_order_insufficient_balance(alice_converter, operator, weth):
    """Test cannot create order with insufficient balance"""
    # No tokens sent to converter

    with boa.reverts("Insufficient balance"):
        with boa.env.prank(operator):
            alice_converter.create_order(
                weth.address,
                2 * 10**18,
                3000 * 10**18,
                boa.env.timestamp + 3600,
                b"\x00" * 32
            )


def test_cannot_create_multiple_active_orders(alice_converter, alice, weth, operator):
    """Test cannot create order when one is already active"""
    weth.mint(alice, 10 * 10**18)
    with boa.env.prank(alice):
        weth.transfer(alice_converter.address, 10 * 10**18)

    # Create first order
    with boa.env.prank(operator):
        alice_converter.create_order(
            weth.address,
            2 * 10**18,
            3000 * 10**18,
            boa.env.timestamp + 3600,
            b"\x00" * 32
        )

    # Try to create second order (should fail)
    with boa.reverts("Active order exists"):
        with boa.env.prank(operator):
            alice_converter.create_order(
                weth.address,
                2 * 10**18,
                3000 * 10**18,
                boa.env.timestamp + 3600,
                b"\x00" * 32
            )


def test_emergency_withdraw(alice_converter, alice, weth):
    """Test owner can emergency withdraw tokens"""
    weth.mint(alice, 10 * 10**18)
    with boa.env.prank(alice):
        weth.transfer(alice_converter.address, 5 * 10**18)

    # Owner withdraws
    with boa.env.prank(alice):
        alice_converter.emergency_withdraw_token(weth.address, 5 * 10**18)

    # Check tokens returned to owner
    assert weth.balanceOf(alice) == 10 * 10**18
    assert weth.balanceOf(alice_converter.address) == 0


def test_non_owner_cannot_emergency_withdraw(alice_converter, alice, weth, bob):
    """Test non-owner cannot emergency withdraw"""
    weth.mint(alice, 10 * 10**18)
    with boa.env.prank(alice):
        weth.transfer(alice_converter.address, 5 * 10**18)

    # Bob tries to withdraw (should fail)
    with boa.reverts("Only owner"):
        with boa.env.prank(bob):
            alice_converter.emergency_withdraw_token(weth.address, 5 * 10**18)
