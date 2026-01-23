"""
Improved License Client with Built-in Trial
- 3-day trial on first run (automatic)
- Seamless activation experience
- No manual scripts needed
- Works perfectly with .exe bundle
"""
import os
import sys
import json
import uuid
import hashlib
import platform
import subprocess
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import logging

logger = logging.getLogger(__name__)


class ImprovedLicenseClient:
    """
    License Client with Built-in Trial and Better UX
    
    Features:
    - Automatic 3-day trial on first run
    - One-time license activation prompt
    - Seamless user experience
    - Hardware ID binding
    - Online + Offline verification
    """
    
    TRIAL_DAYS = 3  # Free trial period
    
    def __init__(self, 
                 license_server_url: str,
                 license_file: str = "license.dat",
                 offline_grace_days: int = 7):
        """Initialize License Client"""
        self.server_url = license_server_url.rstrip('/')
        self.license_file = license_file
        self.offline_grace_days = offline_grace_days
        
        # Generate hardware ID
        self.hardware_id = self._get_hardware_id()
        
        # License state
        self.license_data: Optional[Dict] = None
        self.is_valid: bool = False
        self.license_tier: str = "NONE"
        self.is_trial: bool = False
        self.trial_days_remaining: int = 0
    
    
    def _get_hardware_id(self) -> str:
        """Generate unique hardware ID"""
        identifiers = []
        
        try:
            # Windows
            if platform.system() == "Windows":
                try:
                    cpu_id = subprocess.check_output(
                        'wmic cpu get ProcessorId', 
                        shell=True
                    ).decode().split('\n')[1].strip()
                    identifiers.append(cpu_id)
                except:
                    pass
                
                try:
                    mb_serial = subprocess.check_output(
                        'wmic baseboard get SerialNumber',
                        shell=True
                    ).decode().split('\n')[1].strip()
                    identifiers.append(mb_serial)
                except:
                    pass
            
            # Linux
            elif platform.system() == "Linux":
                try:
                    with open('/etc/machine-id', 'r') as f:
                        identifiers.append(f.read().strip())
                except:
                    pass
            
            # MAC Address
            try:
                mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                               for elements in range(0, 2*6, 2)][::-1])
                identifiers.append(mac)
            except:
                pass
            
            # Platform info
            identifiers.extend([
                platform.machine(),
                platform.processor(),
                platform.system()
            ])
            
            # Combine and hash
            combined = '|'.join(filter(None, identifiers))
            hw_hash = hashlib.sha256(combined.encode()).hexdigest()
            
            return hw_hash
            
        except Exception as e:
            logger.error(f"Failed to generate hardware ID: {e}")
            raise Exception("Hardware identification failed")
    
    
    def _get_encryption_key(self) -> bytes:
        """Derive encryption key from hardware ID"""
        salt = b'BigMotion_Trading_Bot_v2'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.hardware_id.encode()))
        return key
    
    
    def _encrypt_data(self, data: Dict) -> bytes:
        """Encrypt data"""
        try:
            key = self._get_encryption_key()
            f = Fernet(key)
            json_data = json.dumps(data)
            encrypted = f.encrypt(json_data.encode())
            return encrypted
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    
    def _decrypt_data(self, encrypted_data: bytes) -> Dict:
        """Decrypt data"""
        try:
            key = self._get_encryption_key()
            f = Fernet(key)
            decrypted = f.decrypt(encrypted_data)
            data = json.loads(decrypted.decode())
            return data
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise Exception("License file corrupted or tampered")
    
    
    def check_or_start_trial(self) -> Tuple[bool, str]:
        """
        Check if trial is active or start new trial
        
        Returns:
            Tuple of (is_valid: bool, message: str)
        """
        # Check if license file exists
        if os.path.exists(self.license_file):
            # Existing license - verify it
            return self.verify_license()
        
        # No license file - start trial
        return self._start_trial()
    
    
    def _start_trial(self) -> Tuple[bool, str]:
        """Start new trial period"""
        try:
            trial_start = datetime.now()
            trial_end = trial_start + timedelta(days=self.TRIAL_DAYS)
            
            trial_data = {
                'type': 'TRIAL',
                'hardware_id': self.hardware_id,
                'started_at': trial_start.isoformat(),
                'expires_at': trial_end.isoformat(),
                'tier': 'TRIAL'
            }
            
            # Save trial license
            encrypted = self._encrypt_data(trial_data)
            with open(self.license_file, 'wb') as f:
                f.write(encrypted)
            
            self.is_trial = True
            self.trial_days_remaining = self.TRIAL_DAYS
            self.is_valid = True
            self.license_tier = "TRIAL"
            
            logger.info(f"✅ Trial started: {self.TRIAL_DAYS} days")
            
            return True, f"Trial started! You have {self.TRIAL_DAYS} days to test BigMotion Trading Bot."
            
        except Exception as e:
            logger.error(f"Failed to start trial: {e}")
            return False, "Could not start trial - please contact support"
    
    
    def verify_license(self) -> Tuple[bool, str]:
        """
        Verify license validity
        
        Returns:
            Tuple of (is_valid: bool, message: str)
        """
        try:
            # Load license file
            if not os.path.exists(self.license_file):
                return False, "No license found"
            
            with open(self.license_file, 'rb') as f:
                encrypted_data = f.read()
            
            self.license_data = self._decrypt_data(encrypted_data)
            
            # Verify hardware ID
            if self.license_data['hardware_id'] != self.hardware_id:
                return False, "License is bound to different hardware"
            
            # Check if trial
            if self.license_data.get('type') == 'TRIAL':
                return self._verify_trial()
            
            # Check expiration
            expiry_str = self.license_data.get('expiry')
            if expiry_str and expiry_str != 'lifetime':
                expiry = datetime.fromisoformat(expiry_str)
                
                if datetime.now() > expiry:
                    return False, f"License expired on {expiry.strftime('%Y-%m-%d')}"
            
            # Verify online (if possible)
            self._verify_online_silent()
            
            # License is valid
            self.is_valid = True
            self.license_tier = self.license_data.get('tier', 'UNKNOWN')
            
            # Calculate days remaining
            if expiry_str and expiry_str != 'lifetime':
                days_remaining = (datetime.fromisoformat(expiry_str) - datetime.now()).days
                return True, f"License valid - {self.license_tier} ({days_remaining} days remaining)"
            else:
                return True, f"License valid - {self.license_tier} (Lifetime)"
            
        except Exception as e:
            logger.error(f"License verification failed: {e}")
            return False, f"Verification error: {str(e)}"
    
    
    def _verify_trial(self) -> Tuple[bool, str]:
        """Verify trial license"""
        try:
            expiry = datetime.fromisoformat(self.license_data['expires_at'])
            
            if datetime.now() > expiry:
                self.is_trial = False
                self.trial_days_remaining = 0
                return False, "Trial period expired - please activate a license"
            
            # Trial is still valid
            self.is_trial = True
            self.trial_days_remaining = (expiry - datetime.now()).days
            self.is_valid = True
            self.license_tier = "TRIAL"
            
            return True, f"Trial active - {self.trial_days_remaining} days remaining"
            
        except Exception as e:
            logger.error(f"Trial verification failed: {e}")
            return False, "Trial verification error"
    
    
    def _verify_online_silent(self):
        """Silently verify online (doesn't affect validity if fails)"""
        try:
            if self.license_data.get('type') == 'TRIAL':
                return  # Skip online verification for trial
            
            response = requests.post(
                f"{self.server_url}/api/license/verify",
                json={
                    "license_key": self.license_data.get('license_key'),
                    "hardware_id": self.hardware_id
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('valid'):
                    logger.debug("✅ Online verification passed")
                    
                    # Update last check
                    self.license_data['last_check'] = datetime.now().isoformat()
                    self._save_license()
                    
        except Exception as e:
            logger.debug(f"Online verification skipped: {e}")
            # Silent failure - offline mode
    
    
    def _save_license(self):
        """Save license data"""
        try:
            encrypted = self._encrypt_data(self.license_data)
            with open(self.license_file, 'wb') as f:
                f.write(encrypted)
        except Exception as e:
            logger.error(f"Failed to save license: {e}")
    
    
    def activate_license(self, license_key: str) -> Tuple[bool, str]:
        """
        Activate license with key
        
        Args:
            license_key: License key from purchase
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            logger.info("🔐 Activating license...")
            
            response = requests.post(
                f"{self.server_url}/api/license/activate",
                json={
                    "license_key": license_key,
                    "hardware_id": self.hardware_id,
                    "machine_name": platform.node(),
                    "os": f"{platform.system()} {platform.release()}"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data['success']:
                    # Save license
                    license_info = {
                        'type': 'FULL',
                        'license_key': license_key,
                        'hardware_id': self.hardware_id,
                        'tier': data['tier'],
                        'expiry': data['expiry'],
                        'activated_at': datetime.now().isoformat(),
                        'last_check': datetime.now().isoformat()
                    }
                    
                    # Encrypt and save
                    encrypted = self._encrypt_data(license_info)
                    with open(self.license_file, 'wb') as f:
                        f.write(encrypted)
                    
                    logger.info(f"✅ License activated: {data['tier']}")
                    
                    return True, f"License activated successfully! Tier: {data['tier']}, Expires: {data['expiry']}"
                else:
                    return False, data.get('message', 'Activation failed')
            else:
                return False, f"Server error: {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during activation: {e}")
            return False, "Cannot reach license server - check internet connection"
        except Exception as e:
            logger.error(f"Activation error: {e}")
            return False, str(e)
    
    
    def prompt_activation_if_needed(self) -> bool:
        """
        Interactive activation prompt (for first run or trial expiry)
        
        Returns:
            True if license is valid, False otherwise
        """
        # Check current license status
        is_valid, message = self.check_or_start_trial()
        
        if is_valid:
            # License is good
            if self.is_trial:
                print(f"\n{'='*60}")
                print(f"🎯 TRIAL MODE")
                print(f"{'='*60}")
                print(f"   Days Remaining: {self.trial_days_remaining}")
                print(f"   To activate full license, restart and enter license key")
                print(f"{'='*60}\n")
            else:
                print(f"\n✅ License Valid: {self.license_tier}\n")
            
            return True
        
        # License invalid or trial expired
        print(f"\n{'='*60}")
        print(f"🔐 LICENSE ACTIVATION REQUIRED")
        print(f"{'='*60}")
        print(f"   Status: {message}")
        print(f"{'='*60}\n")
        
        # Ask user what to do
        print("Options:")
        print("  1. Activate with license key")
        print("  2. Purchase license via Telegram bot")
        print("  3. Exit")
        print()
        
        choice = input("Choose option (1-3): ").strip()
        
        if choice == '1':
            # Activate with key
            license_key = input("\nEnter your license key: ").strip()
            
            if not license_key:
                print("❌ No license key provided\n")
                return False
            
            print("\n🔄 Activating license...")
            success, msg = self.activate_license(license_key)
            
            print()
            if success:
                print("="*60)
                print("✅ LICENSE ACTIVATED SUCCESSFULLY!")
                print("="*60)
                print(msg)
                print("="*60)
                print("\n🚀 Bot will start now...\n")
                return True
            else:
                print("="*60)
                print("❌ ACTIVATION FAILED")
                print("="*60)
                print(f"Reason: {msg}")
                print("\nPlease check your license key and try again.")
                print("Or contact support: support@bigmotion.ai")
                print("="*60)
                return False
        
        elif choice == '2':
            # Direct to Telegram bot
            print("\n📱 Purchase License via Telegram:")
            print("   1. Open Telegram")
            print("   2. Search for: @BigMotionLicenseBot")
            print("   3. Click /start and follow instructions")
            print()
            print("After purchase, restart the bot and enter your license key!")
            return False
        
        else:
            # Exit
            print("\nExiting...")
            return False
    
    
    def get_license_info(self) -> Dict:
        """Get current license information"""
        if not self.license_data:
            return {
                'status': 'NO_LICENSE',
                'tier': 'NONE',
                'valid': False
            }
        
        info = {
            'status': 'VALID' if self.is_valid else 'INVALID',
            'tier': self.license_tier,
            'valid': self.is_valid,
            'is_trial': self.is_trial,
            'hardware_id': self.hardware_id[:16] + '...',
        }
        
        if self.is_trial:
            info['trial_days_remaining'] = self.trial_days_remaining
        
        if self.license_data.get('expiry'):
            expiry = self.license_data['expiry']
            if expiry != 'lifetime':
                expiry_date = datetime.fromisoformat(expiry)
                info['expiry'] = expiry_date.strftime('%Y-%m-%d')
                info['days_remaining'] = (expiry_date - datetime.now()).days
            else:
                info['expiry'] = 'Lifetime'
                info['days_remaining'] = 'Unlimited'
        
        return info


# Convenience function for bot integration
def check_license_on_startup(server_url: str) -> Tuple[bool, ImprovedLicenseClient]:
    """
    Easy integration for bot startup
    
    Usage in main.py:
        from utils.license_client_v2 import check_license_on_startup
        
        # At bot startup
        is_valid, license_client = check_license_on_startup("https://license.yourdomain.com")
        if not is_valid:
            print("License check failed - exiting")
            sys.exit(1)
    
    Args:
        server_url: License server URL
        
    Returns:
        Tuple of (is_valid: bool, client: ImprovedLicenseClient)
    """
    try:
        client = ImprovedLicenseClient(server_url)
        is_valid = client.prompt_activation_if_needed()
        return is_valid, client
    except Exception as e:
        print(f"License system error: {e}")
        return False, None
