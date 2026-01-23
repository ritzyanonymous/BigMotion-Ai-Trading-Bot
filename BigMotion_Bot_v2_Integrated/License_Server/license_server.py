"""
Professional License Server - Flask API
Handles license activation, verification, and management

Features:
- License key validation
- Hardware ID binding
- Multi-tier license support
- License activation/deactivation
- SQLite database storage
- Admin API for license management
- Logging and analytics
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import hashlib
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
import logging
from functools import wraps

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('license_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for API access

# Configuration
DATABASE = 'licenses.db'
ADMIN_API_KEY = 'YOUR_ADMIN_API_KEY_HERE'  # Change this!

# License tiers configuration
LICENSE_TIERS = {
    'TRIAL': {
        'duration_days': 7,
        'max_machines': 1,
        'features': ['basic_trading']
    },
    'BASIC': {
        'duration_days': 30,
        'max_machines': 1,
        'features': ['basic_trading', 'ml_predictions']
    },
    'PRO': {
        'duration_days': 365,
        'max_machines': 3,
        'features': ['basic_trading', 'ml_predictions', 'advanced_indicators', 'telegram_alerts']
    },
    'ENTERPRISE': {
        'duration_days': None,  # Lifetime
        'max_machines': 10,
        'features': ['basic_trading', 'ml_predictions', 'advanced_indicators', 'telegram_alerts', 
                     'priority_support', 'custom_strategies']
    }
}


def init_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Licenses table
    c.execute('''
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT UNIQUE NOT NULL,
            tier TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            max_machines INTEGER NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            customer_email TEXT,
            customer_name TEXT,
            notes TEXT
        )
    ''')
    
    # Activations table
    c.execute('''
        CREATE TABLE IF NOT EXISTS activations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT NOT NULL,
            hardware_id TEXT NOT NULL,
            machine_name TEXT,
            os_info TEXT,
            activated_at TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (license_key) REFERENCES licenses (license_key),
            UNIQUE(license_key, hardware_id)
        )
    ''')
    
    # Verification log
    c.execute('''
        CREATE TABLE IF NOT EXISTS verification_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT NOT NULL,
            hardware_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            result TEXT NOT NULL,
            ip_address TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("✅ Database initialized")


def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def require_admin_key(f):
    """Decorator to require admin API key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-Admin-Key')
        if api_key != ADMIN_API_KEY:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function


def generate_license_key(tier: str = 'BASIC', length: int = 25) -> str:
    """
    Generate a unique license key
    
    Format: TIER-XXXXX-XXXXX-XXXXX-XXXXX
    """
    chars = string.ascii_uppercase + string.digits
    key_parts = [tier[:4].upper()]
    
    for _ in range(4):
        part = ''.join(secrets.choice(chars) for _ in range(5))
        key_parts.append(part)
    
    return '-'.join(key_parts)


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })


@app.route('/api/license/activate', methods=['POST'])
def activate_license():
    """
    Activate a license on a specific hardware
    
    Request:
        {
            "license_key": "XXXX-XXXX-XXXX-XXXX",
            "hardware_id": "sha256_hash",
            "machine_name": "optional",
            "os": "optional"
        }
    
    Response:
        {
            "success": true/false,
            "message": "...",
            "tier": "PRO",
            "expiry": "2026-12-31"
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'license_key' not in data or 'hardware_id' not in data:
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            }), 400
        
        license_key = data['license_key'].strip().upper()
        hardware_id = data['hardware_id'].strip()
        machine_name = data.get('machine_name', 'Unknown')
        os_info = data.get('os', 'Unknown')
        
        conn = get_db()
        c = conn.cursor()
        
        # Check if license exists and is active
        c.execute('''
            SELECT * FROM licenses 
            WHERE license_key = ? AND is_active = 1
        ''', (license_key,))
        
        license_row = c.fetchone()
        
        if not license_row:
            logger.warning(f"Invalid license key: {license_key}")
            return jsonify({
                'success': False,
                'message': 'Invalid or inactive license key'
            }), 404
        
        # Check expiration
        if license_row['expires_at']:
            expiry = datetime.fromisoformat(license_row['expires_at'])
            if datetime.now() > expiry:
                logger.warning(f"Expired license: {license_key}")
                return jsonify({
                    'success': False,
                    'message': f'License expired on {expiry.strftime("%Y-%m-%d")}'
                }), 403
        
        # Check if hardware already activated
        c.execute('''
            SELECT * FROM activations
            WHERE license_key = ? AND hardware_id = ? AND is_active = 1
        ''', (license_key, hardware_id))
        
        existing = c.fetchone()
        
        if existing:
            # Update last seen
            c.execute('''
                UPDATE activations
                SET last_seen = ?
                WHERE license_key = ? AND hardware_id = ?
            ''', (datetime.now().isoformat(), license_key, hardware_id))
            conn.commit()
            
            logger.info(f"Re-activation: {license_key} on {hardware_id[:16]}...")
        else:
            # Check machine limit
            c.execute('''
                SELECT COUNT(*) as count FROM activations
                WHERE license_key = ? AND is_active = 1
            ''', (license_key,))
            
            active_count = c.fetchone()['count']
            
            if active_count >= license_row['max_machines']:
                logger.warning(f"Machine limit exceeded: {license_key}")
                return jsonify({
                    'success': False,
                    'message': f'Maximum machines ({license_row["max_machines"]}) already activated'
                }), 403
            
            # Create new activation
            c.execute('''
                INSERT INTO activations 
                (license_key, hardware_id, machine_name, os_info, activated_at, last_seen)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (license_key, hardware_id, machine_name, os_info, 
                  datetime.now().isoformat(), datetime.now().isoformat()))
            conn.commit()
            
            logger.info(f"✅ New activation: {license_key} on {hardware_id[:16]}...")
        
        # Log verification
        c.execute('''
            INSERT INTO verification_log 
            (license_key, hardware_id, timestamp, result, ip_address)
            VALUES (?, ?, ?, ?, ?)
        ''', (license_key, hardware_id, datetime.now().isoformat(), 
              'ACTIVATED', request.remote_addr))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'License activated successfully',
            'tier': license_row['tier'],
            'expiry': license_row['expires_at'] or 'lifetime'
        })
        
    except Exception as e:
        logger.error(f"Activation error: {e}")
        return jsonify({
            'success': False,
            'message': 'Server error during activation'
        }), 500


@app.route('/api/license/verify', methods=['POST'])
def verify_license():
    """
    Verify license validity (heartbeat check)
    
    Request:
        {
            "license_key": "XXXX-XXXX-XXXX-XXXX",
            "hardware_id": "sha256_hash"
        }
    
    Response:
        {
            "valid": true/false,
            "reason": "...",
            "tier": "PRO"
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'license_key' not in data or 'hardware_id' not in data:
            return jsonify({
                'valid': False,
                'reason': 'Missing required fields'
            }), 400
        
        license_key = data['license_key'].strip().upper()
        hardware_id = data['hardware_id'].strip()
        
        conn = get_db()
        c = conn.cursor()
        
        # Check license
        c.execute('''
            SELECT l.*, a.is_active as activation_active
            FROM licenses l
            LEFT JOIN activations a ON l.license_key = a.license_key 
                AND a.hardware_id = ?
            WHERE l.license_key = ?
        ''', (hardware_id, license_key))
        
        row = c.fetchone()
        
        if not row:
            logger.warning(f"Verification failed: License not found {license_key}")
            result = {'valid': False, 'reason': 'License not found'}
        elif not row['is_active']:
            logger.warning(f"Verification failed: License revoked {license_key}")
            result = {'valid': False, 'reason': 'License has been revoked'}
        elif row['activation_active'] != 1:
            logger.warning(f"Verification failed: Not activated on this hardware {license_key}")
            result = {'valid': False, 'reason': 'Not activated on this hardware'}
        elif row['expires_at']:
            expiry = datetime.fromisoformat(row['expires_at'])
            if datetime.now() > expiry:
                logger.warning(f"Verification failed: Expired {license_key}")
                result = {'valid': False, 'reason': f'License expired on {expiry.strftime("%Y-%m-%d")}'}
            else:
                # Valid - update last seen
                c.execute('''
                    UPDATE activations
                    SET last_seen = ?
                    WHERE license_key = ? AND hardware_id = ?
                ''', (datetime.now().isoformat(), license_key, hardware_id))
                conn.commit()
                
                logger.debug(f"✅ Verification passed: {license_key}")
                result = {'valid': True, 'tier': row['tier']}
        else:
            # Lifetime license
            c.execute('''
                UPDATE activations
                SET last_seen = ?
                WHERE license_key = ? AND hardware_id = ?
            ''', (datetime.now().isoformat(), license_key, hardware_id))
            conn.commit()
            
            logger.debug(f"✅ Verification passed: {license_key} (Lifetime)")
            result = {'valid': True, 'tier': row['tier']}
        
        # Log verification
        c.execute('''
            INSERT INTO verification_log 
            (license_key, hardware_id, timestamp, result, ip_address)
            VALUES (?, ?, ?, ?, ?)
        ''', (license_key, hardware_id, datetime.now().isoformat(), 
              'VALID' if result['valid'] else result['reason'], request.remote_addr))
        conn.commit()
        conn.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Verification error: {e}")
        return jsonify({
            'valid': False,
            'reason': 'Server error'
        }), 500


@app.route('/api/license/deactivate', methods=['POST'])
def deactivate_license():
    """Deactivate license on specific hardware"""
    try:
        data = request.get_json()
        
        license_key = data.get('license_key', '').strip().upper()
        hardware_id = data.get('hardware_id', '').strip()
        
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            UPDATE activations
            SET is_active = 0
            WHERE license_key = ? AND hardware_id = ?
        ''', (license_key, hardware_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Deactivated: {license_key} on {hardware_id[:16]}...")
        
        return jsonify({
            'success': True,
            'message': 'License deactivated'
        })
        
    except Exception as e:
        logger.error(f"Deactivation error: {e}")
        return jsonify({
            'success': False,
            'message': 'Server error'
        }), 500


# ==================== ADMIN APIs ====================

@app.route('/api/admin/license/create', methods=['POST'])
@require_admin_key
def admin_create_license():
    """
    Admin: Create new license
    
    Request:
        {
            "tier": "PRO",
            "customer_email": "user@example.com",
            "customer_name": "John Doe",
            "duration_days": 365,  // optional, overrides tier default
            "notes": "Special offer"
        }
    """
    try:
        data = request.get_json()
        
        tier = data.get('tier', 'BASIC').upper()
        if tier not in LICENSE_TIERS:
            return jsonify({'error': 'Invalid tier'}), 400
        
        tier_config = LICENSE_TIERS[tier]
        
        # Generate license key
        license_key = generate_license_key(tier)
        
        # Calculate expiry
        duration_days = data.get('duration_days', tier_config['duration_days'])
        if duration_days:
            expires_at = (datetime.now() + timedelta(days=duration_days)).isoformat()
        else:
            expires_at = None  # Lifetime
        
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO licenses 
            (license_key, tier, created_at, expires_at, max_machines, customer_email, customer_name, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (license_key, tier, datetime.now().isoformat(), expires_at, 
              tier_config['max_machines'], data.get('customer_email'), 
              data.get('customer_name'), data.get('notes')))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Created license: {license_key} ({tier})")
        
        return jsonify({
            'success': True,
            'license_key': license_key,
            'tier': tier,
            'expires_at': expires_at or 'lifetime',
            'max_machines': tier_config['max_machines']
        })
        
    except Exception as e:
        logger.error(f"License creation error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/licenses', methods=['GET'])
@require_admin_key
def admin_list_licenses():
    """Admin: List all licenses"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            SELECT l.*, 
                   COUNT(a.id) as active_machines
            FROM licenses l
            LEFT JOIN activations a ON l.license_key = a.license_key AND a.is_active = 1
            GROUP BY l.id
            ORDER BY l.created_at DESC
        ''')
        
        licenses = []
        for row in c.fetchall():
            licenses.append(dict(row))
        
        conn.close()
        
        return jsonify({
            'success': True,
            'count': len(licenses),
            'licenses': licenses
        })
        
    except Exception as e:
        logger.error(f"List licenses error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/license/<license_key>/revoke', methods=['POST'])
@require_admin_key
def admin_revoke_license(license_key):
    """Admin: Revoke a license"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            UPDATE licenses
            SET is_active = 0
            WHERE license_key = ?
        ''', (license_key.upper(),))
        
        conn.commit()
        conn.close()
        
        logger.info(f"🚫 Revoked license: {license_key}")
        
        return jsonify({
            'success': True,
            'message': f'License {license_key} revoked'
        })
        
    except Exception as e:
        logger.error(f"Revoke error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/stats', methods=['GET'])
@require_admin_key
def admin_stats():
    """Admin: Get license statistics"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Total licenses by tier
        c.execute('''
            SELECT tier, COUNT(*) as count, 
                   SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active
            FROM licenses
            GROUP BY tier
        ''')
        
        tier_stats = [dict(row) for row in c.fetchall()]
        
        # Total activations
        c.execute('SELECT COUNT(*) as count FROM activations WHERE is_active = 1')
        total_activations = c.fetchone()['count']
        
        conn.close()
        
        return jsonify({
            'success': True,
            'tier_stats': tier_stats,
            'total_activations': total_activations
        })
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("🔐 BIGMOTION LICENSE SERVER")
    logger.info("=" * 60)
    
    # Initialize database
    init_database()
    
    # Show admin API key
    logger.info(f"⚠️  Admin API Key: {ADMIN_API_KEY}")
    logger.info("   Change this in production!")
    logger.info("")
    logger.info("🚀 Starting server on http://0.0.0.0:5000")
    logger.info("=" * 60)
    
    # Run server
    app.run(host='0.0.0.0', port=5000, debug=False)
