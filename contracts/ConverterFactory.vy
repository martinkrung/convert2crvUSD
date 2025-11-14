# @version 0.4.3
"""
@title ConverterFactory
@notice Factory contract for deploying personal token converter contracts
@author convert2crvUSD Team
@dev Deploys PersonalConverter instances for each user
     Each user gets their own contract to receive tokens directly
"""

# Interfaces
interface IPersonalConverter:
    def owner() -> address: view

# Events
event PersonalConverterDeployed:
    owner: indexed(address)
    converter: indexed(address)
    deployment_number: uint256

event OwnershipTransferred:
    previous_owner: indexed(address)
    new_owner: indexed(address)

event OperatorUpdated:
    new_operator: indexed(address)

event FeeCollectorUpdated:
    new_fee_collector: indexed(address)

event TokenWhitelistUpdated:
    token: indexed(address)
    whitelisted: bool

# State variables
admin: public(address)
operator: public(address)
fee_collector: public(address)

# CoW Protocol configuration
cow_settlement: public(address)
crv_usd_token: public(address)

# Blueprint address for PersonalConverter
personal_converter_blueprint: public(address)

# Token whitelist (shared across all personal converters)
whitelisted_tokens: public(DynArray[address, 10])
token_whitelist_status: public(HashMap[address, bool])

# Track deployed converters
user_converter: public(HashMap[address, address])  # user -> converter address
all_converters: public(DynArray[address, 1000])
deployment_count: public(uint256)

@deploy
def __init__(
    _admin: address,
    _operator: address,
    _fee_collector: address,
    _cow_settlement: address,
    _crv_usd: address,
    _personal_converter_blueprint: address,
    _initial_whitelist: DynArray[address, 10]
):
    """
    @notice Initialize the factory
    @param _admin Admin address (can update config)
    @param _operator Address authorized to create orders
    @param _fee_collector Address receiving refund fees
    @param _cow_settlement CoW Protocol GPv2Settlement address
    @param _crv_usd crvUSD token address
    @param _personal_converter_blueprint Blueprint address for PersonalConverter
    @param _initial_whitelist Initial set of whitelisted tokens
    """
    assert _admin != empty(address), "Invalid admin"
    assert _operator != empty(address), "Invalid operator"
    assert _fee_collector != empty(address), "Invalid fee collector"
    assert _cow_settlement != empty(address), "Invalid settlement"
    assert _crv_usd != empty(address), "Invalid crvUSD"
    assert _personal_converter_blueprint != empty(address), "Invalid blueprint"

    self.admin = _admin
    self.operator = _operator
    self.fee_collector = _fee_collector
    self.cow_settlement = _cow_settlement
    self.crv_usd_token = _crv_usd
    self.personal_converter_blueprint = _personal_converter_blueprint

    # Initialize whitelist
    for token: address in _initial_whitelist:
        if token != empty(address) and not self.token_whitelist_status[token]:
            self.whitelisted_tokens.append(token)
            self.token_whitelist_status[token] = True
            log TokenWhitelistUpdated(token, True)

@external
def deploy_personal_converter(user: address) -> address:
    """
    @notice Deploy a personal converter contract for a user
    @param user The user who will own the converter
    @return The address of the deployed converter
    @dev Can be called by anyone. If user already has a converter, returns existing address
         Uses create_from_blueprint for efficient deployment
    """
    assert user != empty(address), "Invalid user"

    # Check if user already has a converter
    existing: address = self.user_converter[user]
    if existing != empty(address):
        return existing

    # Deploy new PersonalConverter from blueprint
    converter: address = create_from_blueprint(
        self.personal_converter_blueprint,
        user,                       # _owner
        self.operator,              # _operator
        self.fee_collector,         # _fee_collector
        self.cow_settlement,        # _cow_settlement
        self.crv_usd_token,         # _crv_usd
        self.whitelisted_tokens,    # _initial_whitelist
        code_offset=3
    )

    # Track the deployment
    self.user_converter[user] = converter
    self.all_converters.append(converter)
    self.deployment_count += 1

    log PersonalConverterDeployed(user, converter, self.deployment_count)

    return converter

@external
@view
def get_user_converter(user: address) -> address:
    """
    @notice Get the converter address for a user
    @param user User address
    @return Converter address (or empty if not deployed)
    """
    return self.user_converter[user]

@external
@view
def has_converter(user: address) -> bool:
    """
    @notice Check if a user has a deployed converter
    @param user User address
    @return True if converter exists
    """
    return self.user_converter[user] != empty(address)

@external
@view
def get_all_converters() -> DynArray[address, 1000]:
    """
    @notice Get all deployed converter addresses
    @return Array of converter addresses
    """
    return self.all_converters

# ========== WHITELIST MANAGEMENT ==========

@external
def add_whitelisted_token(token: address):
    """
    @notice Add a token to the whitelist
    @param token Token address to whitelist
    @dev Only callable by admin. Applies to future deployments
    """
    assert msg.sender == self.admin, "Only admin"
    assert token != empty(address), "Invalid token"
    assert not self.token_whitelist_status[token], "Already whitelisted"

    self.whitelisted_tokens.append(token)
    self.token_whitelist_status[token] = True

    log TokenWhitelistUpdated(token, True)

@external
def remove_whitelisted_token(token: address):
    """
    @notice Remove a token from the whitelist
    @param token Token address to remove
    @dev Only callable by admin. Applies to future deployments
    """
    assert msg.sender == self.admin, "Only admin"
    assert self.token_whitelist_status[token], "Not whitelisted"

    # Remove from array
    for i: uint256 in range(10):
        if i >= len(self.whitelisted_tokens):
            break
        if self.whitelisted_tokens[i] == token:
            # Swap with last element and pop
            last_idx: uint256 = len(self.whitelisted_tokens) - 1
            if i != last_idx:
                self.whitelisted_tokens[i] = self.whitelisted_tokens[last_idx]
            self.whitelisted_tokens.pop()
            break

    self.token_whitelist_status[token] = False

    log TokenWhitelistUpdated(token, False)

@external
@view
def is_token_whitelisted(token: address) -> bool:
    """
    @notice Check if a token is whitelisted
    @param token Token address to check
    @return True if token is whitelisted
    """
    return self.token_whitelist_status[token]

@external
@view
def get_whitelisted_tokens() -> DynArray[address, 10]:
    """
    @notice Get all whitelisted tokens
    @return Array of whitelisted token addresses
    """
    return self.whitelisted_tokens

# ========== ADMIN FUNCTIONS ==========

@external
def set_operator(new_operator: address):
    """
    @notice Update the operator address
    @param new_operator New operator address
    @dev Only callable by admin. Applies to future deployments
    """
    assert msg.sender == self.admin, "Only admin"
    assert new_operator != empty(address), "Invalid operator"

    self.operator = new_operator
    log OperatorUpdated(new_operator)

@external
def set_fee_collector(new_fee_collector: address):
    """
    @notice Update the fee collector address
    @param new_fee_collector New fee collector address
    @dev Only callable by admin. Applies to future deployments
    """
    assert msg.sender == self.admin, "Only admin"
    assert new_fee_collector != empty(address), "Invalid fee collector"

    self.fee_collector = new_fee_collector
    log FeeCollectorUpdated(new_fee_collector)

@external
def transfer_admin(new_admin: address):
    """
    @notice Transfer admin role
    @param new_admin New admin address
    @dev Only callable by current admin
    """
    assert msg.sender == self.admin, "Only admin"
    assert new_admin != empty(address), "Invalid admin"

    log OwnershipTransferred(self.admin, new_admin)
    self.admin = new_admin
