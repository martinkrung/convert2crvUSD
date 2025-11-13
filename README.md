# convert2crvUSD

This is a project on arbitrum. The goal is to have a address I can sent any token to. this is a pattern not used yet.

and then the token sent are sold to crvUSD over cowswap. It needs a vyper smart contract who 1. has an internal balance from users which have sent token to it 2. create an order on cowswap 3. the order always has to be to sell token X to crvUSD. 4. the contract needs a list of WETH/USDC/CRV token it accepts. if a token is not on the list, the token can be sent back to the original sender. 5. on sending back the token take a fee of 500 bips. 400 bips send to a fee collector and 100 bips to the addres who payed the fee to send it back. 6. use vyper 4.3

write a lot of test of the vyper code, with boa

if the order sale fails for what ever reason make sure the funds can be send back to the orginal seller, ad some timeout

reseach how cowswap can be used for this and which on-chain contracts have to be used to create that ordres.

think hard about var naming and use the same lingo cross repo

create deploy script for arbitrum

veryfie the contract on arbiscan

use alchemy as rcp

use .evn_arbitrum for keys

use uv to install python stuff

create install script work hard hard hard.
