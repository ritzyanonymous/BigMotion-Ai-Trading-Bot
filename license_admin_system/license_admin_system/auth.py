"""
Authentication Module
Handles admin user authentication and management
"""
import hashlib
import secrets
from datetime import datetime
from typing import Optional, Dict


class Auth:
    def __init__(self, database):
        self.db = database
    
    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256 with salt"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}${password_hash}"
    
    def verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against stored hash"""
        try:
            salt, password_hash = stored_hash.split('$')
            test_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            return test_hash == password_hash
        except Exception:
            return False
    
    def create_admin(self, username: str, password: str) -> int:
        """Create new admin user"""
        password_hash = self.hash_password(password)
        
        query = '''
            INSERT INTO admins (username, password_hash, created_at)
            VALUES (?, ?, ?)
        '''
        admin_id = self.db.execute_update(
            query,
            (username, password_hash, datetime.now())
        )
        
        return admin_id
    
    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate admin user"""
        query = 'SELECT * FROM admins WHERE username = ?'
        results = self.db.execute_query(query, (username,))
        
        if not results:
            return None
        
        admin = dict(results[0])
        
        if self.verify_password(password, admin['password_hash']):
            # Update last login
            self.update_last_login(admin['id'])
            return admin
        
        return None
    
    def update_last_login(self, admin_id: int):
        """Update last login timestamp"""
        query = 'UPDATE admins SET last_login = ? WHERE id = ?'
        self.db.execute_update(query, (datetime.now(), admin_id))
    
    def change_password(self, admin_id: int, current_password: str, new_password: str) -> bool:
        """Change admin password"""
        # Get current admin
        query = 'SELECT * FROM admins WHERE id = ?'
        results = self.db.execute_query(query, (admin_id,))
        
        if not results:
            return False
        
        admin = dict(results[0])
        
        # Verify current password
        if not self.verify_password(current_password, admin['password_hash']):
            return False
        
        # Update password
        new_hash = self.hash_password(new_password)
        update_query = 'UPDATE admins SET password_hash = ? WHERE id = ?'
        self.db.execute_update(update_query, (new_hash, admin_id))
        
        return True
    
    def admin_exists(self) -> bool:
        """Check if any admin user exists"""
        query = 'SELECT COUNT(*) as count FROM admins'
        result = self.db.execute_query(query)[0]
        return result['count'] > 0
    
    def get_admin(self, admin_id: int) -> Optional[Dict]:
        """Get admin by ID"""
        query = 'SELECT id, username, created_at, last_login FROM admins WHERE id = ?'
        results = self.db.execute_query(query, (admin_id,))
        
        if results:
            return dict(results[0])
        return None
