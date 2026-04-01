# 🎛️ BigMotion AutoFX - License Admin Dashboard

Professional web-based admin system for managing customer licenses.

## ✨ FEATURES

### Dashboard
- 📊 Real-time statistics (active licenses, trials, MRR, ARR)
- 📈 Revenue trend charts (last 6 months)
- 🥧 License distribution breakdown
- 👀 Recent licenses overview
- ⚡ Quick actions panel

### License Management
- ➕ Create new licenses (trial, monthly, yearly, lifetime)
- 👁️ View all licenses with pagination
- 🔍 Search and filter (by status, type, email)
- ⏱️ Extend license duration
- 🚫 Revoke licenses (with reason tracking)
- ✅ Re-activate revoked licenses
- 📝 Track license usage and last seen

### Security
- 🔐 Password-protected admin access
- 🔒 Secure session management
- 📋 Audit logging (coming soon)
- 🌐 HTTPS support
- 🛡️ IP whitelist support (optional)

### Analytics
- 💰 Monthly Recurring Revenue (MRR)
- 💵 Annual Recurring Revenue (ARR)
- 📊 Trial conversion tracking
- 📉 Churn rate monitoring
- 📈 Revenue projections

---

## 📦 PACKAGE CONTENTS

```
license_admin_system/
├── app.py                   # Main Flask application
├── database.py              # Database operations
├── license_manager.py       # License business logic
├── auth.py                  # Authentication system
├── requirements.txt         # Python dependencies
├── DEPLOYMENT_GUIDE.md      # Step-by-step AWS deployment
├── README.md                # This file
│
├── templates/               # HTML templates
│   ├── base.html           # Base template
│   ├── login.html          # Login page
│   ├── dashboard.html      # Main dashboard
│   ├── licenses.html       # License listing
│   ├── create_license.html # Create new license
│   ├── license_detail.html # License details
│   ├── reports.html        # Reports page
│   ├── settings.html       # Settings page
│   └── change_password.html # Change password
│
└── database/               # SQLite database (created on first run)
    └── licenses.db         # Main database file
```

---

## 🚀 QUICK START

### Option 1: AWS Lightsail (Recommended)

**Follow the complete deployment guide:**

1. Read `DEPLOYMENT_GUIDE.md`
2. Upload files to your server
3. Install dependencies
4. Configure nginx
5. Set up SSL
6. Access at https://admin.bigmotionautofx.com

**Time:** ~30 minutes

---

### Option 2: Local Testing

**For testing on your local machine:**

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py

# Open browser
http://localhost:5000

# Login
Username: admin
Password: admin123
```

---

## 🎯 DEFAULT CREDENTIALS

**⚠️ CHANGE THESE IMMEDIATELY AFTER FIRST LOGIN!**

- **Username:** admin
- **Password:** admin123

**To change:**
1. Login to dashboard
2. Go to Settings → Change Password
3. Enter new secure password

---

## 💾 DATABASE

### Location:
```
database/licenses.db
```

### Tables:
- **licenses** - All customer licenses
- **usage_stats** - License usage tracking
- **admins** - Admin users
- **audit_log** - Action audit trail
- **payments** - Payment tracking (optional)

### Backup:
```bash
# Manual backup
cp database/licenses.db database/licenses_backup.db

# Automated (set up cron job)
# See DEPLOYMENT_GUIDE.md for details
```

---

## 🔧 CONFIGURATION

### Environment Variables:

```bash
# Secret key for session encryption
export SECRET_KEY="your-random-secret-key-here"

# Database path (optional)
export DATABASE_PATH="database/licenses.db"
```

### In Production:

Set these in the systemd service file:

```ini
Environment="SECRET_KEY=your-random-secret-key-here"
Environment="DATABASE_PATH=/path/to/database.db"
```

---

## 📊 PRICING TIERS

The system supports these license types:

| Type | Duration | Price |
|------|----------|-------|
| Trial | 3 days | Free |
| Monthly | 30 days | $49/month |
| Yearly | 365 days | $499/year |
| Lifetime | Forever | $2,999 one-time |

**Edit these in:** `templates/create_license.html`

---

## 🔄 OPERATIONS

### Create License:

```python
# Via dashboard
Licenses → Create New → Fill form → Create

# Or via API (coming soon)
POST /api/licenses
{
    "email": "customer@email.com",
    "license_type": "monthly",
    "duration_days": 30
}
```

### Extend License:

```
License Details → Enter days → Extend
```

### Revoke License:

```
License Details → Enter reason → Revoke License
```

---

## 🛠️ MAINTENANCE

### View Logs:

```bash
# If running as systemd service
sudo journalctl -u license-admin -f

# If running manually
# Logs appear in terminal
```

### Restart Service:

```bash
sudo systemctl restart license-admin
```

### Update Files:

```bash
# Stop service
sudo systemctl stop license-admin

# Upload new files
# ... upload via SCP ...

# Start service
sudo systemctl start license-admin
```

---

## 🔐 SECURITY

### Best Practices:

1. ✅ Change default admin password
2. ✅ Use strong secret key
3. ✅ Enable HTTPS (via Let's Encrypt)
4. ✅ Regular database backups
5. ✅ Keep dependencies updated
6. ⚠️ Optional: IP whitelist for admin access
7. ⚠️ Optional: 2FA (coming soon)

### IP Whitelist (Optional):

Edit nginx config:

```nginx
location / {
    allow YOUR_IP_ADDRESS;
    deny all;
    proxy_pass http://127.0.0.1:5000;
}
```

---

## 📈 FUTURE ENHANCEMENTS

**Coming Soon:**
- [ ] Email notifications (license created, expiry warnings)
- [ ] Payment integration (Stripe, PayPal)
- [ ] Customer self-service portal
- [ ] Two-factor authentication (2FA)
- [ ] Advanced analytics and reports
- [ ] Export to Excel/CSV
- [ ] API endpoints for integration
- [ ] Webhook support
- [ ] Multi-admin support with roles

**Want a feature? Let me know!**

---

## 🐛 TROUBLESHOOTING

### Dashboard Won't Start:

```bash
# Check service status
sudo systemctl status license-admin

# Check logs
sudo journalctl -u license-admin -n 50
```

### Can't Access via Browser:

```bash
# Check nginx
sudo systemctl status nginx
sudo nginx -t
sudo systemctl reload nginx

# Check DNS
nslookup admin.bigmotionautofx.com
```

### Database Errors:

```bash
# Check file exists
ls -lh database/licenses.db

# Check permissions
sudo chown -R ubuntu:ubuntu /path/to/license_admin

# Reinitialize (⚠️ DELETES ALL DATA!)
rm database/licenses.db
python app.py  # Creates new database
```

---

## 📞 SUPPORT

**Need Help?**

1. Check `DEPLOYMENT_GUIDE.md` for detailed instructions
2. Review error logs: `sudo journalctl -u license-admin -f`
3. Verify all steps were completed correctly
4. Check file permissions
5. Test in local environment first

---

## ✅ CHECKLIST

**Before Going Live:**

- [ ] Files uploaded to server
- [ ] Dependencies installed
- [ ] nginx configured
- [ ] SSL certificate installed
- [ ] DNS A record created
- [ ] Systemd service created and started
- [ ] Default admin password changed
- [ ] Test license creation
- [ ] Database backup configured
- [ ] Firewall rules set

**You're ready!** 🎉

---

## 🎉 YOU'RE ALL SET!

**Your admin dashboard is ready to manage customer licenses professionally!**

**Access it at:** https://admin.bigmotionautofx.com

**Features:**
- ✅ Create/manage licenses
- ✅ Track revenue
- ✅ Monitor trials
- ✅ View analytics
- ✅ Professional interface
- ✅ Mobile-friendly
- ✅ Secure & reliable

**Start managing your licenses like a pro!** 💎

---

**Version:** 1.0.0  
**Last Updated:** February 2026  
**License:** Proprietary (BigMotion AutoFX)
