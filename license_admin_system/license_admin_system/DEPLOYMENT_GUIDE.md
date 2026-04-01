# 🚀 LICENSE ADMIN DASHBOARD - AWS LIGHTSAIL DEPLOYMENT GUIDE

## 📋 OVERVIEW

This guide will help you deploy the BigMotion AutoFX License Admin Dashboard on your existing AWS Lightsail server (98.87.31.222).

**URL:** https://admin.bigmotionautofx.com  
**Server:** AWS Lightsail (98.87.31.222)  
**Tech Stack:** Flask + SQLite + nginx  

---

## 🎯 QUICK OVERVIEW

1. Upload files to server
2. Install Python dependencies
3. Configure nginx subdomain
4. Set up SSL certificate
5. Create systemd service
6. Start dashboard
7. Login and use!

**Total Time:** ~30 minutes

---

## 📦 STEP 1: UPLOAD FILES TO SERVER

### From Your Local Machine:

```powershell
# Navigate to where you extracted the admin system
cd C:\Downloads\license_admin_system

# Upload to server
scp -i "C:\Users\USER\Downloads\LightsailDefaultKey-us-east-1.pem" -r . ubuntu@98.87.31.222:/home/ubuntu/license_admin
```

**Or upload as ZIP:**

```powershell
# Zip the folder first
Compress-Archive -Path license_admin_system -DestinationPath license_admin.zip

# Upload ZIP
scp -i "C:\Users\USER\Downloads\LightsailDefaultKey-us-east-1.pem" license_admin.zip ubuntu@98.87.31.222:/home/ubuntu/

# SSH to server
ssh -i "C:\Users\USER\Downloads\LightsailDefaultKey-us-east-1.pem" ubuntu@98.87.31.222

# Extract
cd /home/ubuntu
unzip license_admin.zip
mv license_admin_system license_admin
```

---

## 🔧 STEP 2: INSTALL DEPENDENCIES

### On the Server (via SSH):

```bash
# Navigate to admin directory
cd /home/ubuntu/license_admin

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python3 app.py &
# Wait 5 seconds for it to create database
sleep 5
# Kill it
pkill -f app.py

# You should see:
# "No admin user found. Creating default admin..."
# "Username: admin"
# "Password: admin123"
```

**✅ Database created at:** `/home/ubuntu/license_admin/database/licenses.db`

---

## 🌐 STEP 3: CONFIGURE NGINX SUBDOMAIN

### Create nginx Configuration:

```bash
sudo nano /etc/nginx/sites-available/admin.bigmotionautofx.com
```

**Paste this configuration:**

```nginx
server {
    listen 80;
    server_name admin.bigmotionautofx.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Enable the site:**

```bash
sudo ln -s /etc/nginx/sites-available/admin.bigmotionautofx.com /etc/nginx/sites-enabled/

# Test nginx configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

---

## 🔒 STEP 4: SET UP SSL CERTIFICATE

### Using Certbot (Same as your main site):

```bash
# Install certbot if not already installed
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d admin.bigmotionautofx.com

# Follow prompts:
# - Enter email address
# - Agree to terms
# - Choose to redirect HTTP to HTTPS (recommended: Yes)
```

**✅ SSL certificate installed!**

---

## 🎬 STEP 5: CREATE SYSTEMD SERVICE

This keeps your admin dashboard running 24/7, even after server restart.

### Create Service File:

```bash
sudo nano /etc/systemd/system/license-admin.service
```

**Paste this configuration:**

```ini
[Unit]
Description=BigMotion AutoFX License Admin Dashboard
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/license_admin
Environment="PATH=/home/ubuntu/license_admin/venv/bin"
Environment="SECRET_KEY=YOUR_RANDOM_SECRET_KEY_HERE_CHANGE_THIS"
ExecStart=/home/ubuntu/license_admin/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**⚠️ IMPORTANT:** Change `YOUR_RANDOM_SECRET_KEY_HERE_CHANGE_THIS` to a random string!

**Generate a secret key:**

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
# Copy the output and paste it in the service file
```

### Enable and Start Service:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable license-admin

# Start service
sudo systemctl start license-admin

# Check status
sudo systemctl status license-admin
```

**Expected output:**
```
● license-admin.service - BigMotion AutoFX License Admin Dashboard
   Loaded: loaded
   Active: active (running)
```

---

## 🎯 STEP 6: CONFIGURE DNS

### In Your Domain Registrar (e.g., GoDaddy, Namecheap):

Add an A record:

```
Type: A
Name: admin
Value: 98.87.31.222
TTL: 600
```

**Full domain:** admin.bigmotionautofx.com → 98.87.31.222

**Wait 5-15 minutes for DNS propagation.**

---

## ✅ STEP 7: TEST AND LOGIN

### Test the Dashboard:

```bash
# Check if service is running
sudo systemctl status license-admin

# Check logs
sudo journalctl -u license-admin -f
```

### Access Dashboard:

1. Open browser
2. Go to: **https://admin.bigmotionautofx.com**
3. Login with:
   - **Username:** admin
   - **Password:** admin123

**✅ YOU'RE IN!**

---

## 🔐 STEP 8: CHANGE DEFAULT PASSWORD (CRITICAL!)

**IMMEDIATELY after first login:**

1. Click **Settings** in navigation
2. Click **Change Password**
3. Enter:
   - Current Password: `admin123`
   - New Password: `[Your Secure Password]`
   - Confirm Password: `[Your Secure Password]`
4. Click **Change Password**

**✅ Admin password secured!**

---

## 🎨 FEATURES YOU CAN NOW USE

### Dashboard:
- View active licenses count
- See trial users
- Track MRR (Monthly Recurring Revenue)
- Track ARR (Annual Recurring Revenue)
- View revenue trends
- See license distribution

### License Management:
- Create new licenses
- View all licenses
- Filter by status/type
- Search by email
- Extend licenses
- Revoke licenses
- View license details
- Track usage

---

## 🔄 MAINTENANCE COMMANDS

### Start/Stop Dashboard:

```bash
# Start
sudo systemctl start license-admin

# Stop
sudo systemctl stop license-admin

# Restart
sudo systemctl restart license-admin

# View logs
sudo journalctl -u license-admin -f
```

### Update Dashboard:

```bash
# Stop service
sudo systemctl stop license-admin

# Navigate to directory
cd /home/ubuntu/license_admin

# Pull new files (or upload new files via SCP)
# ... upload new files ...

# Activate venv
source venv/bin/activate

# Install any new dependencies
pip install -r requirements.txt

# Restart service
sudo systemctl start license-admin
```

### Database Backup:

```bash
# Create backup
cp /home/ubuntu/license_admin/database/licenses.db /home/ubuntu/license_admin/database/licenses_backup_$(date +%Y%m%d).db

# Or copy to safe location
scp /home/ubuntu/license_admin/database/licenses.db [your-backup-location]
```

**💡 TIP:** Set up a daily backup cron job!

---

## 🐛 TROUBLESHOOTING

### Dashboard Won't Start:

```bash
# Check service status
sudo systemctl status license-admin

# Check logs for errors
sudo journalctl -u license-admin -n 50

# Check if port 5000 is in use
sudo lsof -i :5000

# Kill any process using port 5000
sudo kill -9 $(sudo lsof -t -i:5000)

# Restart service
sudo systemctl restart license-admin
```

### Can't Access via Browser:

```bash
# Check nginx status
sudo systemctl status nginx

# Check nginx configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx

# Check DNS
nslookup admin.bigmotionautofx.com

# Check SSL
sudo certbot certificates
```

### Database Issues:

```bash
# Check if database exists
ls -lh /home/ubuntu/license_admin/database/licenses.db

# Check permissions
sudo chown -R ubuntu:ubuntu /home/ubuntu/license_admin

# Reinitialize database (⚠️ DELETES ALL DATA!)
rm /home/ubuntu/license_admin/database/licenses.db
python3 app.py  # Will create new database
```

---

## 🔒 SECURITY BEST PRACTICES

### 1. Change Default Admin Password ✅
**Done in Step 8**

### 2. Use Strong Secret Key ✅
**Set in systemd service file**

### 3. Enable Firewall:

```bash
# Allow SSH, HTTP, HTTPS
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable
```

### 4. Restrict Admin Access (Optional):

Only allow admin dashboard access from your IP:

```bash
sudo nano /etc/nginx/sites-available/admin.bigmotionautofx.com
```

Add before `location /`:

```nginx
# Only allow from your IP
allow YOUR_IP_ADDRESS;
deny all;
```

### 5. Regular Backups:

Set up daily database backups:

```bash
# Create backup script
nano /home/ubuntu/backup_licenses.sh
```

```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
cp /home/ubuntu/license_admin/database/licenses.db /home/ubuntu/backups/licenses_$DATE.db
# Keep only last 30 days
find /home/ubuntu/backups -name "licenses_*.db" -mtime +30 -delete
```

```bash
# Make executable
chmod +x /home/ubuntu/backup_licenses.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add line:
# 0 2 * * * /home/ubuntu/backup_licenses.sh
```

---

## 📊 USAGE EXAMPLES

### Create a New License:

1. Click **Licenses** → **Create New License**
2. Enter customer email
3. Select license type (trial/monthly/yearly/lifetime)
4. Click **Create License**
5. Copy license key and send to customer

### Extend a License:

1. Go to **Licenses**
2. Find customer license
3. Click **View** (eye icon)
4. Enter days to extend
5. Click **Extend**

### Revoke a License (Refund):

1. Find license
2. Click **View**
3. Enter revocation reason: "Customer refund"
4. Click **Revoke License**
5. License immediately deactivated

---

## 🎯 NEXT STEPS

**You're all set!** 🎉

Your admin dashboard is now:
- ✅ Running 24/7 on AWS Lightsail
- ✅ Accessible at https://admin.bigmotionautofx.com
- ✅ Secured with SSL
- ✅ Auto-starts on server reboot
- ✅ Ready to manage customer licenses

**What to do now:**
1. Login and explore the dashboard
2. Create a test license
3. Bookmark the admin URL
4. Set up regular backups
5. Start managing your customer licenses!

---

## 📞 NEED HELP?

**Common Issues:**
- Dashboard not loading → Check systemd service status
- SSL errors → Rerun certbot
- Database errors → Check file permissions
- Can't login → Reset admin password via command line

**Check Logs:**
```bash
sudo journalctl -u license-admin -f
```

---

**Your License Admin Dashboard is LIVE!** 🚀

Access it at: **https://admin.bigmotionautofx.com**

Username: admin  
Password: [Change this immediately!]
