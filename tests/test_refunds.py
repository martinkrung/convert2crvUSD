"""
Tests for refund mechanism with fees
"""
import pytest
import boa


def test_refund_non_whitelisted_token(converter, random_token, funded_bob, fee_collector, alice):
    """Test refunding non-whitelisted token with fees"""
    deposit_amount = 1000 * 10**18

    # Bob deposits random token
    with boa.env.prank(funded_bob):
        random_token.approve(converter.address, deposit_amount)
        converter.deposit(random_token.address, deposit_amount)

    # Get initial balances
    initial_bob = random_token.balanceOf(funded_bob)
    initial_collector = random_token.balanceOf(fee_collector)
    initial_alice = random_token.balanceOf(alice)

    # Alice initiates refund
    with boa.env.prank(alice):
        converter.refund_non_whitelisted_token(funded_bob, random_token.address)

    # Calculate expected amounts
    # Total fee: 5% = 50 tokens
    # To collector: 4% = 40 tokens
    # To initiator: 1% = 10 tokens
    # To user: 95% = 950 tokens
    expected_to_user = deposit_amount * 9500 // 10000
    expected_to_collector = deposit_amount * 400 // 10000
    expected_to_initiator = deposit_amount * 100 // 10000

    # Verify balances
    assert random_token.balanceOf(funded_bob) == initial_bob + expected_to_user
    assert random_token.balanceOf(fee_collector) == initial_collector + expected_to_collector
    assert random_token.balanceOf(alice) == initial_alice + expected_to_initiator

    # Verify contract balance cleared
    assert converter.get_user_balance(funded_bob, random_token.address) == 0


def test_refund_whitelisted_token_fails(converter, weth, funded_alice, alice):
    """Test refunding whitelisted token fails"""
    deposit_amount = 10 * 10**18

    with boa.env.prank(funded_alice):
        weth.approve(converter.address, deposit_amount)
        converter.deposit(weth.address, deposit_amount)

    with boa.env.prank(alice):
        with boa.reverts("Token is whitelisted"):
            converter.refund_non_whitelisted_token(funded_alice, weth.address)


def test_refund_crv_usd_fails(converter, crv_usd, alice):
    """Test refunding crvUSD fails"""
    with boa.env.prank(alice):
        with boa.reverts("Cannot refund crvUSD"):
            converter.refund_non_whitelisted_token(alice, crv_usd.address)


def test_refund_zero_balance_fails(converter, random_token, funded_bob, alice):
    """Test refunding with zero balance fails"""
    # Bob has no balance
    with boa.env.prank(alice):
        with boa.reverts("No balance to refund"):
            converter.refund_non_whitelisted_token(funded_bob, random_token.address)


def test_refund_fee_calculation_edge_cases(converter, random_token, funded_bob, fee_collector, alice):
    """Test fee calculation with edge case amounts"""
    # Small amount
    small_amount = 100

    with boa.env.prank(funded_bob):
        random_token.approve(converter.address, small_amount)
        converter.deposit(random_token.address, small_amount)

    initial_collector = random_token.balanceOf(fee_collector)
    initial_alice = random_token.balanceOf(alice)

    with boa.env.prank(alice):
        converter.refund_non_whitelisted_token(funded_bob, random_token.address)

    # Even with small amounts, fees should be calculated
    collector_fee = random_token.balanceOf(fee_collector) - initial_collector
    initiator_fee = random_token.balanceOf(alice) - initial_alice

    # Collector should get 4% (rounded down)
    assert collector_fee == small_amount * 400 // 10000

    # Initiator should get 1% (rounded down)
    assert initiator_fee == small_amount * 100 // 10000


def test_multiple_refunds_different_users(converter, random_token, funded_bob, alice, bob, fee_collector):
    """Test multiple users can get refunds"""
    amount_bob = 1000 * 10**18
    amount_alice = 500 * 10**18

    # Bob deposits
    with boa.env.prank(funded_bob):
        random_token.approve(converter.address, amount_bob)
        converter.deposit(random_token.address, amount_bob)

    # Alice gets tokens and deposits
    random_token.mint(alice, amount_alice)
    with boa.env.prank(alice):
        random_token.approve(converter.address, amount_alice)
        converter.deposit(random_token.address, amount_alice)

    # Someone refunds Bob
    with boa.env.prank(bob):
        converter.refund_non_whitelisted_token(funded_bob, random_token.address)

    # Someone refunds Alice
    with boa.env.prank(bob):
        converter.refund_non_whitelisted_token(alice, random_token.address)

    # Both should have received refunds minus fees
    assert converter.get_user_balance(funded_bob, random_token.address) == 0
    assert converter.get_user_balance(alice, random_token.address) == 0


def test_refund_after_token_removed_from_whitelist(converter, owner, weth, funded_alice, alice, fee_collector):
    """Test refund works after token is removed from whitelist"""
    deposit_amount = 10 * 10**18

    # Alice deposits WETH (whitelisted)
    with boa.env.prank(funded_alice):
        weth.approve(converter.address, deposit_amount)
        converter.deposit(weth.address, deposit_amount)

    # Owner removes WETH from whitelist
    with boa.env.prank(owner):
        converter.remove_whitelisted_token(weth.address)

    # Now WETH can be refunded with fees
    initial_alice = weth.balanceOf(funded_alice)

    with boa.env.prank(alice):
        converter.refund_non_whitelisted_token(funded_alice, weth.address)

    # Alice should have received 95% of her deposit
    expected_refund = deposit_amount * 9500 // 10000
    assert weth.balanceOf(funded_alice) == initial_alice + expected_refund
