"""
BigMotion AutoFX - License Admin Dashboard
Main Flask Application
"""
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
import os
from datetime import datetime, timedelta
import secrets

# Import our modules
from database import Database
from license_manager import LicenseManager
from auth import Auth

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Configuration
app.config['DATABASE_PATH'] = os.environ.get('DATABASE_PATH', 'database/licenses.db')
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)

# Initialize components
db = Database(app.config['DATABASE_PATH'])
license_manager = LicenseManager(db)
auth = Auth(db)


# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# Routes
@app.route('/')
@login_required
def dashboard():
    """Main dashboard page"""
    stats = license_manager.get_statistics()
    recent_licenses = license_manager.get_recent_licenses(limit=10)
    revenue_data = license_manager.get_revenue_trend(months=6)
    
    return render_template('dashboard.html', 
                         stats=stats,
                         recent_licenses=recent_licenses,
                         revenue_data=revenue_data)


@app.route('/licenses')
@login_required
def licenses():
    """All licenses page"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    type_filter = request.args.get('type', 'all')
    search = request.args.get('search', '')
    
    licenses_data = license_manager.get_licenses(
        page=page,
        per_page=20,
        status=status_filter,
        license_type=type_filter,
        search=search
    )
    
    return render_template('licenses.html',
                         licenses=licenses_data['licenses'],
                         page=page,
                         total_pages=licenses_data['total_pages'],
                         total_count=licenses_data['total_count'],
                         status_filter=status_filter,
                         type_filter=type_filter,
                         search=search)


@app.route('/license/create', methods=['GET', 'POST'])
@login_required
def create_license():
    """Create new license"""
    if request.method == 'POST':
        email = request.form.get('email')
        license_type = request.form.get('license_type')
        duration_days = request.form.get('duration_days', type=int)
        send_email = request.form.get('send_email') == 'on'
        
        try:
            license_data = license_manager.create_license(
                email=email,
                license_type=license_type,
                duration_days=duration_days
            )
            
            if send_email:
                # TODO: Send email to customer
                pass
            
            flash(f'License created successfully! License Key: {license_data["license_key"]}', 'success')
            return redirect(url_for('license_detail', license_id=license_data['id']))
            
        except Exception as e:
            flash(f'Error creating license: {str(e)}', 'danger')
    
    return render_template('create_license.html')


@app.route('/license/<int:license_id>')
@login_required
def license_detail(license_id):
    """View license details"""
    license_data = license_manager.get_license(license_id)
    
    if not license_data:
        flash('License not found.', 'danger')
        return redirect(url_for('licenses'))
    
    usage_stats = license_manager.get_license_usage(license_id)
    
    return render_template('license_detail.html',
                         license=license_data,
                         usage_stats=usage_stats)


@app.route('/license/<int:license_id>/extend', methods=['POST'])
@login_required
def extend_license(license_id):
    """Extend license duration"""
    days = request.form.get('days', type=int)
    
    try:
        license_manager.extend_license(license_id, days)
        flash(f'License extended by {days} days.', 'success')
    except Exception as e:
        flash(f'Error extending license: {str(e)}', 'danger')
    
    return redirect(url_for('license_detail', license_id=license_id))


@app.route('/license/<int:license_id>/revoke', methods=['POST'])
@login_required
def revoke_license(license_id):
    """Revoke license"""
    reason = request.form.get('reason', 'Revoked by admin')
    
    try:
        license_manager.revoke_license(license_id, reason)
        flash('License revoked successfully.', 'success')
    except Exception as e:
        flash(f'Error revoking license: {str(e)}', 'danger')
    
    return redirect(url_for('licenses'))


@app.route('/license/<int:license_id>/activate', methods=['POST'])
@login_required
def activate_license(license_id):
    """Re-activate revoked license"""
    try:
        license_manager.activate_license(license_id)
        flash('License activated successfully.', 'success')
    except Exception as e:
        flash(f'Error activating license: {str(e)}', 'danger')
    
    return redirect(url_for('license_detail', license_id=license_id))


@app.route('/reports')
@login_required
def reports():
    """Reports and analytics page"""
    # Get report data
    monthly_revenue = license_manager.get_monthly_revenue()
    conversion_stats = license_manager.get_conversion_stats()
    churn_stats = license_manager.get_churn_stats()
    
    return render_template('reports.html',
                         monthly_revenue=monthly_revenue,
                         conversion_stats=conversion_stats,
                         churn_stats=churn_stats)


@app.route('/api/stats')
@login_required
def api_stats():
    """API endpoint for dashboard stats"""
    stats = license_manager.get_statistics()
    return jsonify(stats)


@app.route('/api/revenue-trend')
@login_required
def api_revenue_trend():
    """API endpoint for revenue trend data"""
    months = request.args.get('months', 6, type=int)
    data = license_manager.get_revenue_trend(months)
    return jsonify(data)


@app.route('/settings')
@login_required
def settings():
    """Settings page"""
    return render_template('settings.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = auth.authenticate(username, password)
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session.permanent = True
            
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
        else:
            user_id = session['user_id']
            if auth.change_password(user_id, current_password, new_password):
                flash('Password changed successfully!', 'success')
                return redirect(url_for('settings'))
            else:
                flash('Current password is incorrect.', 'danger')
    
    return render_template('change_password.html')


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500


if __name__ == '__main__':
    # Initialize database
    db.initialize()
    
    # Check if admin user exists, create default if not
    if not auth.admin_exists():
        print("No admin user found. Creating default admin...")
        print("Username: admin")
        print("Password: admin123")
        print("⚠️ PLEASE CHANGE THIS PASSWORD IMMEDIATELY!")
        auth.create_admin('admin', 'admin123')
    
    # Run development server
    app.run(host='0.0.0.0', port=5000, debug=True)
