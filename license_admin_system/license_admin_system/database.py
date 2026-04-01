"""
Database module for License Admin System
Handles all database operations using SQLite
"""
import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager


class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        
        # Create database directory if it doesn't exist
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def initialize(self):
        """Initialize database with required tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Licenses table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS licenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    license_key TEXT UNIQUE NOT NULL,
                    license_type TEXT NOT NULL,
                    hardware_id TEXT,
                    created_at DATETIME NOT NULL,
                    expires_at DATETIME,
                    status TEXT NOT NULL DEFAULT 'active',
                    last_seen DATETIME,
                    revoke_reason TEXT,
                    notes TEXT
                )
            ''')
            
            # Create index on email for faster searches
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_licenses_email 
                ON licenses(email)
            ''')
            
            # Create index on status
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_licenses_status 
                ON licenses(status)
            ''')
            
            # Usage statistics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    license_id INTEGER NOT NULL,
                    login_timestamp DATETIME NOT NULL,
                    ip_address TEXT,
                    bot_version TEXT,
                    FOREIGN KEY (license_id) REFERENCES licenses(id)
                )
            ''')
            
            # Admin users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at DATETIME NOT NULL,
                    last_login DATETIME
                )
            ''')
            
            # Audit log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    action TEXT NOT NULL,
                    details TEXT,
                    timestamp DATETIME NOT NULL,
                    FOREIGN KEY (admin_id) REFERENCES admins(id)
                )
            ''')
            
            # Payments table (optional - for tracking payments)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    license_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'USD',
                    payment_method TEXT,
                    transaction_id TEXT,
                    payment_date DATETIME NOT NULL,
                    FOREIGN KEY (license_id) REFERENCES licenses(id)
                )
            ''')
            
            conn.commit()
    
    def execute_query(self, query, params=None):
        """Execute a query and return results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
    
    def execute_update(self, query, params=None):
        """Execute an update/insert query"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.lastrowid
    
    def log_action(self, admin_id, action, details=None):
        """Log admin action to audit log"""
        query = '''
            INSERT INTO audit_log (admin_id, action, details, timestamp)
            VALUES (?, ?, ?, ?)
        '''
        self.execute_update(query, (admin_id, action, details, datetime.now()))
