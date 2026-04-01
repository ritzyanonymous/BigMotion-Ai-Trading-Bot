"""
License Manager Module
Handles all license CRUD operations and business logic
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class LicenseManager:
    def __init__(self, database):
        self.db = database
    
    def generate_license_key(self, email: str) -> str:
        """Generate unique license key"""
        # Create a unique license key based on email and timestamp
        unique_string = f"{email}{datetime.now().isoformat()}{secrets.token_hex(16)}"
        hash_object = hashlib.sha256(unique_string.encode())
        license_key = hash_object.hexdigest()[:32].upper()
        
        # Format as XXXX-XXXX-XXXX-XXXX
        formatted_key = '-'.join([license_key[i:i+8] for i in range(0, 32, 8)])
        return formatted_key
    
    def create_license(self, email: str, license_type: str, duration_days: int = None) -> Dict:
        """Create a new license"""
        # Generate license key
        license_key = self.generate_license_key(email)
        
        # Calculate expiry date
        created_at = datetime.now()
        if license_type == 'trial':
            expires_at = created_at + timedelta(days=3)
        elif license_type == 'monthly':
            expires_at = created_at + timedelta(days=duration_days or 30)
        elif license_type == 'yearly':
            expires_at = created_at + timedelta(days=duration_days or 365)
        elif license_type == 'lifetime':
            expires_at = None  # Never expires
        else:
            expires_at = created_at + timedelta(days=duration_days or 30)
        
        # Insert into database
        query = '''
            INSERT INTO licenses (email, license_key, license_type, created_at, expires_at, status)
            VALUES (?, ?, ?, ?, ?, 'active')
        '''
        license_id = self.db.execute_update(
            query,
            (email, license_key, license_type, created_at, expires_at)
        )
        
        return {
            'id': license_id,
            'email': email,
            'license_key': license_key,
            'license_type': license_type,
            'created_at': created_at,
            'expires_at': expires_at,
            'status': 'active'
        }
    
    def get_license(self, license_id: int) -> Optional[Dict]:
        """Get license by ID"""
        query = 'SELECT * FROM licenses WHERE id = ?'
        results = self.db.execute_query(query, (license_id,))
        
        if results:
            return dict(results[0])
        return None
    
    def get_license_by_key(self, license_key: str) -> Optional[Dict]:
        """Get license by key"""
        query = 'SELECT * FROM licenses WHERE license_key = ?'
        results = self.db.execute_query(query, (license_key,))
        
        if results:
            return dict(results[0])
        return None
    
    def get_licenses(self, page: int = 1, per_page: int = 20, 
                    status: str = 'all', license_type: str = 'all',
                    search: str = '') -> Dict:
        """Get paginated list of licenses with filters"""
        offset = (page - 1) * per_page
        
        # Build query with filters
        where_clauses = []
        params = []
        
        if status != 'all':
            where_clauses.append('status = ?')
            params.append(status)
        
        if license_type != 'all':
            where_clauses.append('license_type = ?')
            params.append(license_type)
        
        if search:
            where_clauses.append('(email LIKE ? OR license_key LIKE ?)')
            search_param = f'%{search}%'
            params.extend([search_param, search_param])
        
        where_sql = ' AND '.join(where_clauses) if where_clauses else '1=1'
        
        # Get total count
        count_query = f'SELECT COUNT(*) as count FROM licenses WHERE {where_sql}'
        count_result = self.db.execute_query(count_query, params)
        total_count = count_result[0]['count']
        
        # Get licenses
        query = f'''
            SELECT * FROM licenses 
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        '''
        params.extend([per_page, offset])
        results = self.db.execute_query(query, params)
        
        licenses = [dict(row) for row in results]
        
        return {
            'licenses': licenses,
            'total_count': total_count,
            'total_pages': (total_count + per_page - 1) // per_page,
            'current_page': page
        }
    
    def get_recent_licenses(self, limit: int = 10) -> List[Dict]:
        """Get most recent licenses"""
        query = '''
            SELECT * FROM licenses 
            ORDER BY created_at DESC 
            LIMIT ?
        '''
        results = self.db.execute_query(query, (limit,))
        return [dict(row) for row in results]
    
    def extend_license(self, license_id: int, days: int):
        """Extend license expiry date"""
        license_data = self.get_license(license_id)
        
        if not license_data:
            raise ValueError('License not found')
        
        if license_data['license_type'] == 'lifetime':
            raise ValueError('Cannot extend lifetime license')
        
        # Calculate new expiry date
        current_expiry = datetime.fromisoformat(license_data['expires_at'])
        new_expiry = current_expiry + timedelta(days=days)
        
        query = 'UPDATE licenses SET expires_at = ? WHERE id = ?'
        self.db.execute_update(query, (new_expiry, license_id))
    
    def revoke_license(self, license_id: int, reason: str = ''):
        """Revoke a license"""
        query = '''
            UPDATE licenses 
            SET status = 'revoked', revoke_reason = ?
            WHERE id = ?
        '''
        self.db.execute_update(query, (reason, license_id))
    
    def activate_license(self, license_id: int):
        """Re-activate a revoked license"""
        query = '''
            UPDATE licenses 
            SET status = 'active', revoke_reason = NULL
            WHERE id = ?
        '''
        self.db.execute_update(query, (license_id,))
    
    def update_last_seen(self, license_key: str, hardware_id: str = None):
        """Update last seen timestamp"""
        params = [datetime.now()]
        query_parts = ['last_seen = ?']
        
        if hardware_id:
            query_parts.append('hardware_id = ?')
            params.append(hardware_id)
        
        params.append(license_key)
        
        query = f'''
            UPDATE licenses 
            SET {', '.join(query_parts)}
            WHERE license_key = ?
        '''
        self.db.execute_update(query, params)
    
    def get_statistics(self) -> Dict:
        """Get dashboard statistics"""
        # Total active licenses
        active_query = "SELECT COUNT(*) as count FROM licenses WHERE status = 'active'"
        active_count = self.db.execute_query(active_query)[0]['count']
        
        # Trial licenses
        trial_query = "SELECT COUNT(*) as count FROM licenses WHERE license_type = 'trial' AND status = 'active'"
        trial_count = self.db.execute_query(trial_query)[0]['count']
        
        # Expired licenses
        expired_query = '''
            SELECT COUNT(*) as count FROM licenses 
            WHERE expires_at < ? AND license_type != 'lifetime' AND status = 'active'
        '''
        expired_count = self.db.execute_query(expired_query, (datetime.now(),))[0]['count']
        
        # Calculate MRR (Monthly Recurring Revenue)
        mrr_query = '''
            SELECT COUNT(*) as count FROM licenses 
            WHERE license_type = 'monthly' AND status = 'active'
        '''
        monthly_licenses = self.db.execute_query(mrr_query)[0]['count']
        mrr = monthly_licenses * 49  # $49 per month
        
        # Calculate ARR (Annual Recurring Revenue)
        arr_query = '''
            SELECT COUNT(*) as count FROM licenses 
            WHERE license_type = 'yearly' AND status = 'active'
        '''
        yearly_licenses = self.db.execute_query(arr_query)[0]['count']
        arr = (monthly_licenses * 49 * 12) + (yearly_licenses * 499)
        
        # License type distribution
        type_query = '''
            SELECT license_type, COUNT(*) as count 
            FROM licenses 
            WHERE status = 'active'
            GROUP BY license_type
        '''
        type_distribution = {row['license_type']: row['count'] 
                           for row in self.db.execute_query(type_query)}
        
        return {
            'active_licenses': active_count,
            'trial_licenses': trial_count,
            'expired_licenses': expired_count,
            'mrr': mrr,
            'arr': arr,
            'license_distribution': type_distribution
        }
    
    def get_revenue_trend(self, months: int = 6) -> List[Dict]:
        """Get revenue trend for last N months"""
        # This is a simplified version - you would calculate actual revenue
        # based on payment records
        trend_data = []
        
        for i in range(months, 0, -1):
            month_start = datetime.now() - timedelta(days=30 * i)
            month_end = datetime.now() - timedelta(days=30 * (i - 1))
            
            query = '''
                SELECT COUNT(*) as count FROM licenses
                WHERE created_at >= ? AND created_at < ? AND license_type = 'monthly'
            '''
            monthly_count = self.db.execute_query(query, (month_start, month_end))[0]['count']
            
            trend_data.append({
                'month': month_start.strftime('%B'),
                'revenue': monthly_count * 49  # Simplified calculation
            })
        
        return trend_data
    
    def get_license_usage(self, license_id: int) -> List[Dict]:
        """Get usage statistics for a license"""
        query = '''
            SELECT * FROM usage_stats 
            WHERE license_id = ? 
            ORDER BY login_timestamp DESC 
            LIMIT 50
        '''
        results = self.db.execute_query(query, (license_id,))
        return [dict(row) for row in results]
    
    def log_usage(self, license_key: str, ip_address: str = None, bot_version: str = None):
        """Log license usage"""
        license_data = self.get_license_by_key(license_key)
        
        if license_data:
            query = '''
                INSERT INTO usage_stats (license_id, login_timestamp, ip_address, bot_version)
                VALUES (?, ?, ?, ?)
            '''
            self.db.execute_update(
                query,
                (license_data['id'], datetime.now(), ip_address, bot_version)
            )
            
            # Update last seen
            self.update_last_seen(license_key)
    
    def get_conversion_stats(self) -> Dict:
        """Get trial to paid conversion statistics"""
        # Total trials
        trial_query = "SELECT COUNT(*) as count FROM licenses WHERE license_type = 'trial'"
        total_trials = self.db.execute_query(trial_query)[0]['count']
        
        # Converted trials (users who had trial and now have paid license)
        # This is simplified - you'd track this better with a conversions table
        converted_query = '''
            SELECT COUNT(DISTINCT email) as count FROM licenses
            WHERE email IN (
                SELECT email FROM licenses WHERE license_type = 'trial'
            ) AND license_type IN ('monthly', 'yearly', 'lifetime')
        '''
        converted = self.db.execute_query(converted_query)[0]['count']
        
        conversion_rate = (converted / total_trials * 100) if total_trials > 0 else 0
        
        return {
            'total_trials': total_trials,
            'converted': converted,
            'conversion_rate': round(conversion_rate, 2)
        }
    
    def get_monthly_revenue(self) -> List[Dict]:
        """Get monthly revenue breakdown"""
        # This would integrate with payment records in production
        query = '''
            SELECT 
                strftime('%Y-%m', created_at) as month,
                license_type,
                COUNT(*) as count
            FROM licenses
            WHERE status = 'active'
            GROUP BY month, license_type
            ORDER BY month DESC
            LIMIT 12
        '''
        results = self.db.execute_query(query)
        return [dict(row) for row in results]
    
    def get_churn_stats(self) -> Dict:
        """Get churn statistics"""
        # Licenses that expired this month
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0)
        
        expired_query = '''
            SELECT COUNT(*) as count FROM licenses
            WHERE expires_at >= ? AND expires_at < ? 
            AND license_type != 'lifetime'
            AND status = 'active'
        '''
        next_month = month_start + timedelta(days=32)
        next_month = next_month.replace(day=1)
        
        expired = self.db.execute_query(expired_query, (month_start, next_month))[0]['count']
        
        # Active at start of month
        active_query = '''
            SELECT COUNT(*) as count FROM licenses
            WHERE created_at < ? AND status = 'active'
        '''
        active_start = self.db.execute_query(active_query, (month_start,))[0]['count']
        
        churn_rate = (expired / active_start * 100) if active_start > 0 else 0
        
        return {
            'churned_this_month': expired,
            'active_start_month': active_start,
            'churn_rate': round(churn_rate, 2)
        }
