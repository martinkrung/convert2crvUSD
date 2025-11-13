"""
Verification script for Convert2CrvUSD on Arbiscan
Verifies the deployed contract source code on Arbiscan
"""
import os
import sys
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv


# Load environment variables
env_path = Path(__file__).parent.parent / ".env_arbitrum"
load_dotenv(env_path)


def load_deployment_info():
    """Load deployment information from deployment.json"""
    deployment_file = Path(__file__).parent.parent / "deployment.json"

    if not deployment_file.exists():
        print("❌ deployment.json not found. Please run deploy.py first.")
        sys.exit(1)

    with open(deployment_file, 'r') as f:
        return json.load(f)


def get_contract_source():
    """Read the contract source code"""
    contract_path = Path(__file__).parent.parent / "contracts" / "Convert2CrvUSD.vy"

    if not contract_path.exists():
        print(f"❌ Contract file not found: {contract_path}")
        sys.exit(1)

    with open(contract_path, 'r') as f:
        return f.read()


def get_interface_sources():
    """Read all interface files"""
    interfaces_dir = Path(__file__).parent.parent / "interfaces"
    interface_sources = {}

    for interface_file in interfaces_dir.glob("*.vyi"):
        with open(interface_file, 'r') as f:
            interface_sources[interface_file.name] = f.read()

    return interface_sources


def verify_on_arbiscan(contract_address, constructor_args):
    """
    Verify contract on Arbiscan using their API

    Note: Arbiscan verification for Vyper contracts may require manual verification
    through their web interface as API support for Vyper is limited.
    """
    api_key = os.getenv("ARBISCAN_API_KEY")

    if not api_key:
        print("❌ ARBISCAN_API_KEY not found in .env_arbitrum")
        print("Please add your Arbiscan API key to .env_arbitrum")
        sys.exit(1)

    print(f"🔍 Verifying contract {contract_address} on Arbiscan...")

    # For Vyper contracts, we need to use the source code verification
    source_code = get_contract_source()

    # Arbiscan API endpoint
    api_url = "https://api.arbiscan.io/api"

    # Prepare verification request
    # Note: This is for Solidity contracts. Vyper verification may differ.
    # You may need to verify manually through Arbiscan's web interface.

    print("\n⚠️  Note: Arbiscan API has limited support for Vyper contracts.")
    print("For best results, consider verifying manually:")
    print(f"1. Go to https://arbiscan.io/address/{contract_address}#code")
    print("2. Click 'Verify and Publish'")
    print("3. Select 'Vyper (Experimental)'")
    print("4. Upload your contract source code")
    print("5. Enter constructor arguments (if needed)")

    print("\n📋 Constructor arguments for verification:")
    print(json.dumps(constructor_args, indent=2))

    # Try API verification anyway
    response = input("\nTry API verification? (y/n): ")
    if response.lower() != 'y':
        print("Skipping API verification. Please verify manually.")
        return

    # Prepare the data
    data = {
        "apikey": api_key,
        "module": "contract",
        "action": "verifysourcecode",
        "contractaddress": contract_address,
        "sourceCode": source_code,
        "codeformat": "solidity-single-file",  # May need to be adjusted for Vyper
        "contractname": "Convert2CrvUSD",
        "compilerversion": "v0.4.3",  # Vyper version
        "optimizationUsed": "0",
        "runs": "200",
        "constructorArguements": encode_constructor_args(constructor_args),
    }

    try:
        response = requests.post(api_url, data=data)
        result = response.json()

        if result["status"] == "1":
            guid = result["result"]
            print(f"✅ Verification submitted. GUID: {guid}")
            print("Checking verification status...")

            # Check status
            time.sleep(5)  # Wait a bit before checking
            check_verification_status(api_key, guid)
        else:
            print(f"❌ Verification failed: {result.get('result', 'Unknown error')}")
            print("\nPlease verify manually through Arbiscan web interface.")

    except Exception as e:
        print(f"❌ API verification failed: {e}")
        print("\nPlease verify manually through Arbiscan web interface.")


def encode_constructor_args(args):
    """Encode constructor arguments for verification"""
    from eth_abi import encode

    # Encode the constructor arguments
    # Format: (address owner, address operator, address fee_collector, address cow_settlement, address crv_usd)
    encoded = encode(
        ["address", "address", "address", "address", "address"],
        [
            args["owner"],
            args["operator"],
            args["fee_collector"],
            args["cow_settlement"],
            args["crv_usd"]
        ]
    )

    return encoded.hex()


def check_verification_status(api_key, guid):
    """Check the verification status"""
    api_url = "https://api.arbiscan.io/api"

    for i in range(10):  # Try 10 times
        time.sleep(3)

        response = requests.get(api_url, params={
            "apikey": api_key,
            "module": "contract",
            "action": "checkverifystatus",
            "guid": guid
        })

        result = response.json()

        if result["status"] == "1":
            if "Pass" in result["result"]:
                print("✅ Contract verified successfully!")
                return
            elif "Pending" in result["result"]:
                print(f"⏳ Verification pending... ({i+1}/10)")
                continue
            else:
                print(f"❌ Verification failed: {result['result']}")
                return
        else:
            print(f"❌ Error checking status: {result.get('result', 'Unknown error')}")
            return

    print("⏱️  Verification taking longer than expected. Check Arbiscan manually.")


def create_verification_guide():
    """Create a guide for manual verification"""
    guide_path = Path(__file__).parent.parent / "VERIFICATION_GUIDE.md"

    deployment_info = load_deployment_info()

    guide_content = f"""# Manual Verification Guide for Arbiscan

## Contract Information
- **Contract Address**: `{deployment_info['contract_address']}`
- **Compiler**: Vyper
- **Compiler Version**: 0.4.3
- **Optimization**: Disabled

## Constructor Arguments

```
Owner: {deployment_info['deployer']}
Operator: {deployment_info['deployer']}
Fee Collector: {os.getenv('FEE_COLLECTOR', 'N/A')}
CoW Settlement: {deployment_info['cow_settlement']}
crvUSD: {deployment_info['crv_usd']}
```

## Verification Steps

1. Go to [Arbiscan Contract Verification](https://arbiscan.io/address/{deployment_info['contract_address']}#code)

2. Click "Verify and Publish"

3. Select the following options:
   - Compiler Type: **Vyper (Experimental)**
   - Compiler Version: **v0.4.3**
   - License Type: **None** (or select appropriate license)

4. Upload Files:
   - Main contract: `contracts/Convert2CrvUSD.vy`
   - Interfaces (if required):
     - `interfaces/IERC20.vyi`
     - `interfaces/IGPv2Settlement.vyi`
     - `interfaces/IERC1271.vyi`

5. Enter Constructor Arguments:
   - You may need to ABI-encode the constructor arguments
   - Use the values listed above

6. Complete the CAPTCHA and click "Verify and Publish"

## Troubleshooting

If verification fails:
- Ensure you're using the exact same compiler version (0.4.3)
- Check that all interface files are included
- Verify constructor arguments are correctly encoded
- Make sure the source code matches the deployed bytecode

## ABI-Encoded Constructor Arguments

If Arbiscan requires ABI-encoded constructor arguments, use this Python snippet:

```python
from eth_abi import encode

args = encode(
    ["address", "address", "address", "address", "address"],
    [
        "{deployment_info['deployer']}",
        "{deployment_info['deployer']}",
        "{os.getenv('FEE_COLLECTOR', '0x0000000000000000000000000000000000000000')}",
        "{deployment_info['cow_settlement']}",
        "{deployment_info['crv_usd']}"
    ]
)
print(args.hex())
```

## Resources

- [Arbiscan Verify Contract](https://arbiscan.io/verifyContract)
- [Vyper Documentation](https://docs.vyperlang.org/)
- [CoW Protocol Docs](https://docs.cow.fi/)
"""

    with open(guide_path, 'w') as f:
        f.write(guide_content)

    print(f"\n📖 Verification guide created: {guide_path}")


def main():
    """Main verification function"""
    print("=" * 60)
    print("Convert2CrvUSD Verification Script")
    print("=" * 60)

    # Load deployment info
    deployment_info = load_deployment_info()
    print(f"\n📍 Contract Address: {deployment_info['contract_address']}")

    # Create verification guide
    create_verification_guide()

    # Prepare constructor args
    constructor_args = {
        "owner": deployment_info['deployer'],
        "operator": deployment_info['deployer'],
        "fee_collector": os.getenv('FEE_COLLECTOR', deployment_info['deployer']),
        "cow_settlement": deployment_info['cow_settlement'],
        "crv_usd": deployment_info['crv_usd']
    }

    # Attempt verification
    verify_on_arbiscan(deployment_info['contract_address'], constructor_args)

    print("\n" + "=" * 60)
    print("Verification process complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
