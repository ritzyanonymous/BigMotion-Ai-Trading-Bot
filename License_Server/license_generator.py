"""
License Key Generator and Management Tool
Admin utility for creating and managing licenses

Usage:
    python license_generator.py --create --tier PRO --email user@example.com
    python license_generator.py --list
    python license_generator.py --revoke LICENSE-KEY
"""
import requests
import argparse
import json
from datetime import datetime
from typing import Optional
import sys

# Configuration
LICENSE_SERVER_URL = "http://localhost:5000"  # Change to your server URL
ADMIN_API_KEY = "YOUR_ADMIN_API_KEY_HERE"  # Must match server's ADMIN_API_KEY


class LicenseManager:
    """Admin tool for license management"""
    
    def __init__(self, server_url: str, admin_key: str):
        self.server_url = server_url.rstrip('/')
        self.admin_key = admin_key
        self.headers = {
            'X-Admin-Key': admin_key,
            'Content-Type': 'application/json'
        }
    
    def create_license(self, 
                      tier: str,
                      email: Optional[str] = None,
                      name: Optional[str] = None,
                      duration_days: Optional[int] = None,
                      notes: Optional[str] = None) -> dict:
        """
        Create a new license
        
        Args:
            tier: License tier (TRIAL, BASIC, PRO, ENTERPRISE)
            email: Customer email
            name: Customer name
            duration_days: Override default tier duration
            notes: Additional notes
            
        Returns:
            License information dictionary
        """
        try:
            payload = {
                'tier': tier.upper(),
                'customer_email': email,
                'customer_name': name,
                'notes': notes
            }
            
            if duration_days:
                payload['duration_days'] = duration_days
            
            response = requests.post(
                f"{self.server_url}/api/admin/license/create",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {'error': f'Server error: {response.status_code}', 'details': response.text}
                
        except Exception as e:
            return {'error': str(e)}
    
    def list_licenses(self) -> dict:
        """List all licenses"""
        try:
            response = requests.get(
                f"{self.server_url}/api/admin/licenses",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {'error': f'Server error: {response.status_code}'}
                
        except Exception as e:
            return {'error': str(e)}
    
    def revoke_license(self, license_key: str) -> dict:
        """Revoke a license"""
        try:
            response = requests.post(
                f"{self.server_url}/api/admin/license/{license_key}/revoke",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {'error': f'Server error: {response.status_code}'}
                
        except Exception as e:
            return {'error': str(e)}
    
    def get_stats(self) -> dict:
        """Get license statistics"""
        try:
            response = requests.get(
                f"{self.server_url}/api/admin/stats",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {'error': f'Server error: {response.status_code}'}
                
        except Exception as e:
            return {'error': str(e)}


def print_license_info(info: dict):
    """Pretty print license information"""
    print("\n" + "="*60)
    print("✅ LICENSE CREATED SUCCESSFULLY")
    print("="*60)
    print(f"License Key:    {info.get('license_key', 'N/A')}")
    print(f"Tier:           {info.get('tier', 'N/A')}")
    print(f"Expires:        {info.get('expires_at', 'N/A')}")
    print(f"Max Machines:   {info.get('max_machines', 'N/A')}")
    print("="*60)
    print("\n⚠️  IMPORTANT: Save this license key securely!")
    print("   Share only with the customer.\n")


def print_license_list(data: dict):
    """Pretty print license list"""
    if 'error' in data:
        print(f"❌ Error: {data['error']}")
        return
    
    licenses = data.get('licenses', [])
    
    print("\n" + "="*80)
    print(f"📋 ALL LICENSES ({data.get('count', 0)} total)")
    print("="*80)
    print(f"{'License Key':<30} {'Tier':<12} {'Status':<10} {'Machines':<10} {'Expires':<15}")
    print("-"*80)
    
    for lic in licenses:
        status = "🟢 Active" if lic['is_active'] else "🔴 Revoked"
        machines = f"{lic['active_machines']}/{lic['max_machines']}"
        expires = lic['expires_at'] if lic['expires_at'] else 'Lifetime'
        if lic['expires_at']:
            expires = expires[:10]  # Just the date
        
        print(f"{lic['license_key']:<30} {lic['tier']:<12} {status:<10} {machines:<10} {expires:<15}")
    
    print("="*80 + "\n")


def print_stats(data: dict):
    """Pretty print statistics"""
    if 'error' in data:
        print(f"❌ Error: {data['error']}")
        return
    
    print("\n" + "="*60)
    print("📊 LICENSE STATISTICS")
    print("="*60)
    
    print("\nLicenses by Tier:")
    for tier_stat in data.get('tier_stats', []):
        print(f"  {tier_stat['tier']:<12} Total: {tier_stat['count']:<5} Active: {tier_stat['active']}")
    
    print(f"\nTotal Active Machines: {data.get('total_activations', 0)}")
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='BigMotion Trading Bot - License Management Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a PRO license for a customer
  python license_generator.py --create --tier PRO --email user@example.com --name "John Doe"
  
  # Create a 30-day TRIAL license
  python license_generator.py --create --tier TRIAL --email trial@example.com
  
  # Create a lifetime ENTERPRISE license
  python license_generator.py --create --tier ENTERPRISE --email vip@example.com --name "VIP Client"
  
  # List all licenses
  python license_generator.py --list
  
  # View statistics
  python license_generator.py --stats
  
  # Revoke a license
  python license_generator.py --revoke PRO-XXXXX-XXXXX-XXXXX-XXXXX

Available Tiers:
  TRIAL       - 7 days, 1 machine
  BASIC       - 30 days, 1 machine  
  PRO         - 365 days, 3 machines
  ENTERPRISE  - Lifetime, 10 machines
        """
    )
    
    # Actions
    parser.add_argument('--create', action='store_true', help='Create new license')
    parser.add_argument('--list', action='store_true', help='List all licenses')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--revoke', type=str, metavar='KEY', help='Revoke license')
    
    # License creation options
    parser.add_argument('--tier', type=str, choices=['TRIAL', 'BASIC', 'PRO', 'ENTERPRISE'],
                       help='License tier')
    parser.add_argument('--email', type=str, help='Customer email')
    parser.add_argument('--name', type=str, help='Customer name')
    parser.add_argument('--days', type=int, help='Override duration in days')
    parser.add_argument('--notes', type=str, help='Additional notes')
    
    # Server configuration
    parser.add_argument('--server', type=str, default=LICENSE_SERVER_URL,
                       help=f'License server URL (default: {LICENSE_SERVER_URL})')
    parser.add_argument('--admin-key', type=str, default=ADMIN_API_KEY,
                       help='Admin API key')
    
    args = parser.parse_args()
    
    # Check if at least one action is specified
    if not any([args.create, args.list, args.stats, args.revoke]):
        parser.print_help()
        sys.exit(1)
    
    # Initialize manager
    manager = LicenseManager(args.server, args.admin_key)
    
    # Execute action
    try:
        if args.create:
            if not args.tier:
                print("❌ Error: --tier is required for creating licenses")
                sys.exit(1)
            
            print(f"\n🔧 Creating {args.tier} license...")
            result = manager.create_license(
                tier=args.tier,
                email=args.email,
                name=args.name,
                duration_days=args.days,
                notes=args.notes
            )
            
            if 'error' in result:
                print(f"❌ Error: {result['error']}")
                if 'details' in result:
                    print(f"   Details: {result['details']}")
            else:
                print_license_info(result)
        
        elif args.list:
            print("\n📋 Fetching licenses...")
            result = manager.list_licenses()
            print_license_list(result)
        
        elif args.stats:
            print("\n📊 Fetching statistics...")
            result = manager.get_stats()
            print_stats(result)
        
        elif args.revoke:
            print(f"\n🚫 Revoking license {args.revoke}...")
            result = manager.revoke_license(args.revoke)
            
            if 'error' in result:
                print(f"❌ Error: {result['error']}")
            else:
                print(f"✅ {result['message']}")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
