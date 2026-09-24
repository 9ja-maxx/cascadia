#!/usr/bin/env python3
"""
CASCADIA PROTOCOL — Intelligent Contract Deployment Utility
===========================================================
Deployment automation script for compiling, deploying, and initializing
the Cascadia Intelligent Contract on GenLayer Testnet / Studio Devnet.

Usage:
    python3 scripts/deploy_cascadia.py [--network studio-dev] [--admin <address>]
"""

import sys
import os
import argparse
from pathlib import Path

DEFAULT_RPC_URLS = {
    "local": "http://localhost:4000/api",
    "studio-dev": "https://studio.genlayer.com/api",
    "testnet": "https://testnet.genlayer.com/api"
}

def inspect_contract(source_path: Path):
    if not source_path.exists():
        raise FileNotFoundError(f"Contract not found at {source_path}")
        
    content = source_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    print(f"Contract loaded: {source_path.name} ({len(lines)} LOC, {len(content)} bytes)")
    
    # Simple syntax validation
    compile(content, str(source_path), "exec")
    print("Contract Python AST syntax verification: PASSED")
    return content

def generate_deployment_payload(source_code: str, admin_address: str):
    return {
        "contract_name": "Cascadia",
        "source_code": source_code,
        "constructor_args": [admin_address],
        "vm_runtime": "genlayer-intelligent-contract-v1"
    }

def main():
    parser = argparse.ArgumentParser(description="Deploy Cascadia Protocol Intelligent Contract to GenLayer")
    parser.add_argument("--network", choices=["local", "studio-dev", "testnet"], default="studio-dev", help="Target GenLayer network")
    parser.add_argument("--admin", default="0x0000000000000000000000000000000000000000", help="Protocol admin address")
    parser.add_argument("--contract", default="contracts/cascadia.py", help="Path to contract Python file")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Simulate deployment payload generation")
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("CASCADIA PROTOCOL — INTELLIGENT CONTRACT DEPLOYER")
    print("=" * 70)
    print(f"Target Network: {args.network} ({DEFAULT_RPC_URLS[args.network]})")
    print(f"Admin Address:  {args.admin}")
    print(f"Contract File:  {args.contract}")
    print("-" * 70)
    
    contract_path = Path(args.contract)
    source = inspect_contract(contract_path)
    payload = generate_deployment_payload(source, args.admin)
    
    print("\nDeployment manifest prepared successfully.")
    print(f"Payload Size: {len(payload['source_code'])} bytes")
    print(f"Constructor Parameters: admin_address={args.admin}")
    
    if args.dry_run:
        print("\n[DRY RUN COMPLETE] To deploy on GenLayer Studio:")
        print("  1. Open https://studio.genlayer.com")
        print("  2. Create a new contract file 'cascadia.py'")
        print("  3. Paste the contents of 'contracts/cascadia.py'")
        print("  4. Click 'Deploy' and copy the resulting deployed contract address.")
        print("  5. Paste the address into frontend/.env or the UI Settings modal.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
