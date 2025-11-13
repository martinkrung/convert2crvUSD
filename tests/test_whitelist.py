"""
Tests for token whitelist management
"""
import pytest
import boa


def test_initial_whitelist(converter, weth, usdc, crv):
    """Test initial whitelisted tokens"""
    assert converter.is_token_whitelisted(weth.address)
    assert converter.is_token_whitelisted(usdc.address)
    assert converter.is_token_whitelisted(crv.address)

    tokens = converter.get_whitelisted_tokens()
    assert len(tokens) == 3
    assert weth.address in tokens
    assert usdc.address in tokens
    assert crv.address in tokens


def test_add_whitelisted_token(converter, owner, random_token):
    """Test adding a token to whitelist"""
    assert not converter.is_token_whitelisted(random_token.address)

    with boa.env.prank(owner):
        converter.add_whitelisted_token(random_token.address)

    assert converter.is_token_whitelisted(random_token.address)
    tokens = converter.get_whitelisted_tokens()
    assert random_token.address in tokens


def test_add_whitelisted_token_non_owner_fails(converter, alice, random_token):
    """Test non-owner cannot add to whitelist"""
    with boa.env.prank(alice):
        with boa.reverts("Only owner"):
            converter.add_whitelisted_token(random_token.address)


def test_add_already_whitelisted_token_fails(converter, owner, weth):
    """Test adding already whitelisted token fails"""
    with boa.env.prank(owner):
        with boa.reverts("Already whitelisted"):
            converter.add_whitelisted_token(weth.address)


def test_remove_whitelisted_token(converter, owner, weth):
    """Test removing a token from whitelist"""
    assert converter.is_token_whitelisted(weth.address)

    with boa.env.prank(owner):
        converter.remove_whitelisted_token(weth.address)

    assert not converter.is_token_whitelisted(weth.address)
    tokens = converter.get_whitelisted_tokens()
    assert weth.address not in tokens


def test_remove_non_whitelisted_token_fails(converter, owner, random_token):
    """Test removing non-whitelisted token fails"""
    with boa.env.prank(owner):
        with boa.reverts("Not whitelisted"):
            converter.remove_whitelisted_token(random_token.address)


def test_remove_whitelisted_token_non_owner_fails(converter, alice, weth):
    """Test non-owner cannot remove from whitelist"""
    with boa.env.prank(alice):
        with boa.reverts("Only owner"):
            converter.remove_whitelisted_token(weth.address)


def test_whitelist_add_remove_cycle(converter, owner, random_token):
    """Test adding and removing a token multiple times"""
    # Add
    with boa.env.prank(owner):
        converter.add_whitelisted_token(random_token.address)
    assert converter.is_token_whitelisted(random_token.address)

    # Remove
    with boa.env.prank(owner):
        converter.remove_whitelisted_token(random_token.address)
    assert not converter.is_token_whitelisted(random_token.address)

    # Add again
    with boa.env.prank(owner):
        converter.add_whitelisted_token(random_token.address)
    assert converter.is_token_whitelisted(random_token.address)


def test_get_whitelisted_tokens_after_modifications(converter, owner, weth, usdc, crv, random_token):
    """Test getting whitelisted tokens after adds and removes"""
    initial_count = len(converter.get_whitelisted_tokens())
    assert initial_count == 3

    # Add token
    with boa.env.prank(owner):
        converter.add_whitelisted_token(random_token.address)

    assert len(converter.get_whitelisted_tokens()) == 4

    # Remove token
    with boa.env.prank(owner):
        converter.remove_whitelisted_token(weth.address)

    tokens = converter.get_whitelisted_tokens()
    assert len(tokens) == 3
    assert weth.address not in tokens
    assert random_token.address in tokens
