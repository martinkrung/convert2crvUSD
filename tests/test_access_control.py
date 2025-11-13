"""
Tests for access control and admin functions
"""
import pytest
import boa


def test_initial_roles(converter, owner, operator, fee_collector):
    """Test initial role assignments"""
    assert converter.owner() == owner
    assert converter.operator() == operator
    assert converter.fee_collector() == fee_collector


def test_set_operator(converter, owner, alice):
    """Test owner can update operator"""
    with boa.env.prank(owner):
        converter.set_operator(alice)

    assert converter.operator() == alice


def test_set_operator_non_owner_fails(converter, alice, bob):
    """Test non-owner cannot update operator"""
    with boa.env.prank(alice):
        with boa.reverts("Only owner"):
            converter.set_operator(bob)


def test_set_fee_collector(converter, owner, alice):
    """Test owner can update fee collector"""
    with boa.env.prank(owner):
        converter.set_fee_collector(alice)

    assert converter.fee_collector() == alice


def test_set_fee_collector_non_owner_fails(converter, alice, bob):
    """Test non-owner cannot update fee collector"""
    with boa.env.prank(alice):
        with boa.reverts("Only owner"):
            converter.set_fee_collector(bob)


def test_transfer_ownership(converter, owner, alice):
    """Test ownership transfer"""
    with boa.env.prank(owner):
        converter.transfer_ownership(alice)

    assert converter.owner() == alice


def test_transfer_ownership_non_owner_fails(converter, alice, bob):
    """Test non-owner cannot transfer ownership"""
    with boa.env.prank(alice):
        with boa.reverts("Only owner"):
            converter.transfer_ownership(bob)


def test_new_owner_has_privileges(converter, owner, alice, bob):
    """Test new owner can exercise owner privileges"""
    # Transfer ownership
    with boa.env.prank(owner):
        converter.transfer_ownership(alice)

    # New owner can set operator
    with boa.env.prank(alice):
        converter.set_operator(bob)

    assert converter.operator() == bob

    # Old owner cannot
    with boa.env.prank(owner):
        with boa.reverts("Only owner"):
            converter.set_operator(owner)


def test_emergency_withdraw(converter, owner, weth, funded_alice):
    """Test emergency withdrawal by owner"""
    deposit_amount = 10 * 10**18

    # Alice deposits
    with boa.env.prank(funded_alice):
        weth.approve(converter.address, deposit_amount)
        converter.deposit(weth.address, deposit_amount)

    # Owner emergency withdraws
    initial_owner_balance = weth.balanceOf(owner)

    with boa.env.prank(owner):
        converter.emergency_withdraw_token(weth.address, deposit_amount)

    assert weth.balanceOf(owner) == initial_owner_balance + deposit_amount


def test_emergency_withdraw_non_owner_fails(converter, alice, weth):
    """Test non-owner cannot emergency withdraw"""
    with boa.env.prank(alice):
        with boa.reverts("Only owner"):
            converter.emergency_withdraw_token(weth.address, 100)


def test_operator_can_create_orders(converter, operator, weth, funded_alice):
    """Test operator can create orders"""
    deposit_amount = 10 * 10**18

    with boa.env.prank(funded_alice):
        weth.approve(converter.address, deposit_amount)
        converter.deposit(weth.address, deposit_amount)

    valid_to = boa.env.vm.state.timestamp + 3600
    app_data = b"\x00" * 32

    with boa.env.prank(operator):
        order_uid = converter.create_order(
            funded_alice,
            weth.address,
            5 * 10**18,
            1000 * 10**18,
            valid_to,
            app_data
        )

    assert order_uid != b"\x00" * 32


def test_operator_can_settle_orders(converter, operator, weth, funded_alice):
    """Test operator can settle orders"""
    deposit_amount = 10 * 10**18

    with boa.env.prank(funded_alice):
        weth.approve(converter.address, deposit_amount)
        converter.deposit(weth.address, deposit_amount)

    valid_to = boa.env.vm.state.timestamp + 3600
    app_data = b"\x00" * 32

    with boa.env.prank(operator):
        order_uid = converter.create_order(
            funded_alice,
            weth.address,
            5 * 10**18,
            1000 * 10**18,
            valid_to,
            app_data
        )

        # Settle
        converter.settle_order(order_uid, 1500 * 10**18)

    order = converter.active_orders(order_uid)
    assert order[6] == False  # is_active


def test_operator_can_cancel_orders(converter, operator, weth, funded_alice):
    """Test operator can cancel orders"""
    deposit_amount = 10 * 10**18

    with boa.env.prank(funded_alice):
        weth.approve(converter.address, deposit_amount)
        converter.deposit(weth.address, deposit_amount)

    valid_to = boa.env.vm.state.timestamp + 3600
    app_data = b"\x00" * 32

    with boa.env.prank(operator):
        order_uid = converter.create_order(
            funded_alice,
            weth.address,
            5 * 10**18,
            1000 * 10**18,
            valid_to,
            app_data
        )

        # Cancel
        converter.cancel_order(order_uid)

    order = converter.active_orders(order_uid)
    assert order[6] == False  # is_active


def test_reject_direct_eth(converter, alice):
    """Test contract rejects direct ETH transfers"""
    with boa.env.prank(alice):
        with boa.reverts("Direct ETH not accepted"):
            boa.env.raw_call(converter.address, value=10**18, data=b"")
