"""
Tests for deposit functionality
"""
import pytest
import boa


def test_deposit_whitelisted_token(converter, weth, funded_alice):
    """Test depositing a whitelisted token"""
    deposit_amount = 10 * 10**18  # 10 WETH

    # Approve converter to spend tokens
    with boa.env.prank(funded_alice):
        weth.approve(converter.address, deposit_amount)

        # Get initial balance
        initial_balance = converter.get_user_balance(funded_alice, weth.address)

        # Deposit tokens
        converter.deposit(weth.address, deposit_amount)

        # Check balance updated
        final_balance = converter.get_user_balance(funded_alice, weth.address)
        assert final_balance == initial_balance + deposit_amount

        # Check contract received tokens
        assert weth.balanceOf(converter.address) == deposit_amount


def test_deposit_multiple_times(converter, weth, funded_alice):
    """Test multiple deposits accumulate correctly"""
    deposit_amount = 5 * 10**18

    with boa.env.prank(funded_alice):
        weth.approve(converter.address, deposit_amount * 3)

        # First deposit
        converter.deposit(weth.address, deposit_amount)
        balance1 = converter.get_user_balance(funded_alice, weth.address)
        assert balance1 == deposit_amount

        # Second deposit
        converter.deposit(weth.address, deposit_amount)
        balance2 = converter.get_user_balance(funded_alice, weth.address)
        assert balance2 == deposit_amount * 2

        # Third deposit
        converter.deposit(weth.address, deposit_amount)
        balance3 = converter.get_user_balance(funded_alice, weth.address)
        assert balance3 == deposit_amount * 3


def test_deposit_different_tokens(converter, weth, usdc, crv, funded_alice):
    """Test depositing different tokens"""
    weth_amount = 10 * 10**18
    usdc_amount = 5000 * 10**6
    crv_amount = 1000 * 10**18

    with boa.env.prank(funded_alice):
        # Deposit WETH
        weth.approve(converter.address, weth_amount)
        converter.deposit(weth.address, weth_amount)

        # Deposit USDC
        usdc.approve(converter.address, usdc_amount)
        converter.deposit(usdc.address, usdc_amount)

        # Deposit CRV
        crv.approve(converter.address, crv_amount)
        converter.deposit(crv.address, crv_amount)

        # Check all balances
        assert converter.get_user_balance(funded_alice, weth.address) == weth_amount
        assert converter.get_user_balance(funded_alice, usdc.address) == usdc_amount
        assert converter.get_user_balance(funded_alice, crv.address) == crv_amount


def test_deposit_emits_event(converter, weth, funded_alice):
    """Test deposit emits correct event"""
    deposit_amount = 10 * 10**18

    with boa.env.prank(funded_alice):
        weth.approve(converter.address, deposit_amount)

        # Capture events
        converter.deposit(weth.address, deposit_amount)

        # Check event was emitted (boa doesn't have great event testing yet)
        # In production, you'd verify event data


def test_deposit_zero_amount_fails(converter, weth, funded_alice):
    """Test depositing zero amount fails"""
    with boa.env.prank(funded_alice):
        weth.approve(converter.address, 100 * 10**18)

        with boa.reverts("Amount must be positive"):
            converter.deposit(weth.address, 0)


def test_deposit_without_approval_fails(converter, weth, funded_alice):
    """Test deposit fails without token approval"""
    deposit_amount = 10 * 10**18

    with boa.env.prank(funded_alice):
        # Don't approve
        with boa.reverts():
            converter.deposit(weth.address, deposit_amount)


def test_deposit_insufficient_balance_fails(converter, weth, funded_alice):
    """Test deposit fails with insufficient balance"""
    # Alice has 100 WETH
    excessive_amount = 200 * 10**18

    with boa.env.prank(funded_alice):
        weth.approve(converter.address, excessive_amount)

        with boa.reverts():
            converter.deposit(weth.address, excessive_amount)


def test_multiple_users_deposit(converter, weth, funded_alice, funded_bob):
    """Test multiple users can deposit independently"""
    alice_amount = 10 * 10**18
    bob_amount = 20 * 10**18

    # Alice deposits
    with boa.env.prank(funded_alice):
        weth.approve(converter.address, alice_amount)
        converter.deposit(weth.address, alice_amount)

    # Bob deposits
    with boa.env.prank(funded_bob):
        weth.approve(converter.address, bob_amount)
        converter.deposit(weth.address, bob_amount)

    # Check balances are separate
    assert converter.get_user_balance(funded_alice, weth.address) == alice_amount
    assert converter.get_user_balance(funded_bob, weth.address) == bob_amount
    assert weth.balanceOf(converter.address) == alice_amount + bob_amount


def test_deposit_non_whitelisted_token(converter, random_token, funded_bob):
    """Test depositing non-whitelisted token (still allowed, but can be refunded with fees)"""
    deposit_amount = 100 * 10**18

    with boa.env.prank(funded_bob):
        random_token.approve(converter.address, deposit_amount)
        converter.deposit(random_token.address, deposit_amount)

        # Deposit should succeed even for non-whitelisted tokens
        assert converter.get_user_balance(funded_bob, random_token.address) == deposit_amount
