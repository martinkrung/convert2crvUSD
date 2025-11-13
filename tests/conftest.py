"""
Test configuration and fixtures for Convert2CrvUSD tests
"""
import pytest
import boa
from eth_account import Account
from eth_utils import to_checksum_address


# Mock ERC20 token for testing
ERC20_CODE = """
# @version 0.4.3

name: public(String[32])
symbol: public(String[32])
decimals: public(uint8)
totalSupply: public(uint256)
balanceOf: public(HashMap[address, uint256])
allowance: public(HashMap[address, HashMap[address, uint256]])

event Transfer:
    sender: indexed(address)
    receiver: indexed(address)
    amount: uint256

event Approval:
    owner: indexed(address)
    spender: indexed(address)
    amount: uint256

@deploy
def __init__(_name: String[32], _symbol: String[32], _decimals: uint8, _supply: uint256):
    self.name = _name
    self.symbol = _symbol
    self.decimals = _decimals
    self.totalSupply = _supply
    self.balanceOf[msg.sender] = _supply

@external
def transfer(to: address, amount: uint256) -> bool:
    assert self.balanceOf[msg.sender] >= amount, "Insufficient balance"
    self.balanceOf[msg.sender] -= amount
    self.balanceOf[to] += amount
    log Transfer(msg.sender, to, amount)
    return True

@external
def transferFrom(sender: address, recipient: address, amount: uint256) -> bool:
    assert self.balanceOf[sender] >= amount, "Insufficient balance"
    assert self.allowance[sender][msg.sender] >= amount, "Insufficient allowance"
    self.balanceOf[sender] -= amount
    self.balanceOf[recipient] += amount
    self.allowance[sender][msg.sender] -= amount
    log Transfer(sender, recipient, amount)
    return True

@external
def approve(spender: address, amount: uint256) -> bool:
    self.allowance[msg.sender][spender] = amount
    log Approval(msg.sender, spender, amount)
    return True

@external
def mint(to: address, amount: uint256):
    self.balanceOf[to] += amount
    self.totalSupply += amount
    log Transfer(empty(address), to, amount)
"""

# Mock GPv2Settlement for testing
SETTLEMENT_CODE = """
# @version 0.4.3

domainSeparator: public(bytes32)
vaultRelayer: public(address)
preSignatures: public(HashMap[bytes32, bool])

@deploy
def __init__(_vault_relayer: address):
    self.vaultRelayer = _vault_relayer
    self.domainSeparator = keccak256("COW_SETTLEMENT_DOMAIN")

@external
def setPreSignature(order_uid: bytes32, signed: bool):
    self.preSignatures[order_uid] = signed
"""


@pytest.fixture(scope="session")
def owner():
    """Deploy account (owner)"""
    return boa.env.generate_address("owner")


@pytest.fixture(scope="session")
def operator():
    """Operator account for creating orders"""
    return boa.env.generate_address("operator")


@pytest.fixture(scope="session")
def fee_collector():
    """Fee collector account"""
    return boa.env.generate_address("fee_collector")


@pytest.fixture(scope="session")
def alice():
    """Test user Alice"""
    return boa.env.generate_address("alice")


@pytest.fixture(scope="session")
def bob():
    """Test user Bob"""
    return boa.env.generate_address("bob")


@pytest.fixture(scope="function")
def weth(owner):
    """Deploy mock WETH token"""
    with boa.env.prank(owner):
        return boa.loads(ERC20_CODE, "Wrapped Ether", "WETH", 18, 10**12 * 10**18)


@pytest.fixture(scope="function")
def usdc(owner):
    """Deploy mock USDC token"""
    with boa.env.prank(owner):
        return boa.loads(ERC20_CODE, "USD Coin", "USDC", 6, 10**12 * 10**6)


@pytest.fixture(scope="function")
def crv(owner):
    """Deploy mock CRV token"""
    with boa.env.prank(owner):
        return boa.loads(ERC20_CODE, "Curve DAO Token", "CRV", 18, 10**12 * 10**18)


@pytest.fixture(scope="function")
def crv_usd(owner):
    """Deploy mock crvUSD token"""
    with boa.env.prank(owner):
        return boa.loads(ERC20_CODE, "Curve USD", "crvUSD", 18, 10**12 * 10**18)


@pytest.fixture(scope="function")
def random_token(owner):
    """Deploy a random token (not whitelisted)"""
    with boa.env.prank(owner):
        return boa.loads(ERC20_CODE, "Random Token", "RND", 18, 10**9 * 10**18)


@pytest.fixture(scope="function")
def vault_relayer(owner):
    """Mock vault relayer address"""
    return boa.env.generate_address("vault_relayer")


@pytest.fixture(scope="function")
def settlement(owner, vault_relayer):
    """Deploy mock CoW Settlement contract"""
    with boa.env.prank(owner):
        return boa.loads(SETTLEMENT_CODE, vault_relayer)


@pytest.fixture(scope="function")
def converter(owner, operator, fee_collector, settlement, crv_usd, weth, usdc, crv):
    """Deploy Convert2CrvUSD contract with whitelisted tokens"""
    with boa.env.prank(owner):
        contract = boa.load(
            "contracts/Convert2CrvUSD.vy",
            owner,
            operator,
            fee_collector,
            settlement.address,
            crv_usd.address
        )

        # Add whitelisted tokens
        contract.add_whitelisted_token(weth.address)
        contract.add_whitelisted_token(usdc.address)
        contract.add_whitelisted_token(crv.address)

        return contract


@pytest.fixture(scope="function")
def funded_alice(alice, weth, usdc, crv):
    """Alice with token balances"""
    weth.mint(alice, 100 * 10**18)  # 100 WETH
    usdc.mint(alice, 100000 * 10**6)  # 100k USDC
    crv.mint(alice, 10000 * 10**18)  # 10k CRV
    return alice


@pytest.fixture(scope="function")
def funded_bob(bob, weth, random_token):
    """Bob with token balances including random token"""
    weth.mint(bob, 50 * 10**18)  # 50 WETH
    random_token.mint(bob, 1000 * 10**18)  # 1000 random tokens
    return bob
