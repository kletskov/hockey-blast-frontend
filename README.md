# Hockey Blast Development Setup

Follow the steps below to set up the development environments for the Hockey Blast project.

## Initial Setup

1. Create a new directory and navigate into it:
    ```bash
    mkdir hockey-blast
    cd hockey-blast
    ```

2. Initialize a new Git repository:
    ```bash
    git init
    ```

3. Clone the frontend repository.
    ```bash
    git clone https://github.com/kletskov/hockey-blast-frontend.git 
    ```




4. Open the application in your browser:
    ```
    http://localhost:5001/
    ```

## Running the Application in Production Mode

### Gunicorn Setup

1. Create a Gunicorn configuration file (`gunicorn_config.py`):
    ```python
    // filepath: /Users/pavelkletskov/hockey-blast-prod/hockey-blast-frontend/gunicorn_config.py
    bind = "0.0.0.0:8000"
    workers = 4
    threads = 2
    timeout = 120
    ```

2. Start Gunicorn:
    ```bash
    ./.venv/bin/gunicorn -c gunicorn_config.py "app:create_app('frontend')"
    ```

### NGINX Setup

1. Install NGINX using Homebrew:
    ```bash
    brew install nginx
    ```

2. Create an NGINX configuration file (`hockey_blast`):
    ```perl
    // filepath: /opt/homebrew/etc/nginx/sites-available/hockey_blast
    server {
        listen 80;
        server_name hockey_blast.local hockey-blast.com www.hockey-blast.com;

        location / {
            return 301 https://$host$request_uri;
        }
    }

    server {
        listen 443 ssl;
        server_name hockey_blast.local hockey-blast.com www.hockey-blast.com;

        ssl_certificate /etc/letsencrypt/live/hockey-blast.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/hockey-blast.com/privkey.pem;

        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_prefer_server_ciphers on;
        ssl_ciphers "ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256";

        location / {
            proxy_pass http://127.0.0.1:8000; # Use IPv4 address explicitly
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        error_page 500 502 503 504 /50x.html;
        location = /50x.html {
            root /opt/homebrew/share/nginx/src;
        }
    }
    ```

3. Create a symbolic link to enable the site:
    ```bash
    sudo ln -s /opt/homebrew/etc/nginx/sites-available/hockey_blast /opt/homebrew/etc/nginx/sites-enabled/
    ```

4. Reload NGINX to apply the configuration:
    ```bash
    sudo /opt/homebrew/bin/nginx -s reload
    ```

### Let's Encrypt Certificate Setup

1. Install Certbot:
    ```bash
    brew install certbot
    ```

2. Obtain a wildcard certificate using manual DNS validation:
    ```bash
    sudo certbot certonly --manual --preferred-challenges=dns -d hockey-blast.com -d "*.hockey-blast.com"
    ```

3. Follow the instructions provided by Certbot to add the necessary DNS TXT records for validation.

4. Reload NGINX to apply the new certificate:
    ```bash
    sudo /opt/homebrew/bin/nginx -s reload
    ```

5. Set up automatic certificate renewal using a `launchd` job:
    ```xml
    // filepath: /Library/LaunchDaemons/com.certbot.renew.plist
    <?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
    <plist version="1.0">
      <dict>
        <key>Label</key>
        <string>com.certbot.renew</string>

        <key>ProgramArguments</key>
        <array>
          <string>/usr/local/bin/certbot</string>
          <string>renew</string>
          <string>--quiet</string>
          <string>--post-hook</string>
          <string>sudo /opt/homebrew/bin/nginx -s reload</string>
        </array>

        <key>StartCalendarInterval</key>
        <array>
          <dict>
            <key>Hour</key>
            <integer>0</integer>
            <key>Minute</key>
            <integer>0</integer>
          </dict>
          <dict>
            <key>Hour</key>
            <integer>12</integer>
            <key>Minute</key>
            <integer>0</integer>
          </dict>
        </array>

        <key>StandardErrorPath</key>
        <string>/var/log/certbot_renew_error.log</string>

        <key>StandardOutPath</key>
        <string>/var/log/certbot_renew_output.log</string>

        <key>RunAtLoad</key>
        <true/>
      </dict>
    </plist>
    ```

6. Load the `launchd` job to ensure automatic renewal:
    ```bash
    sudo launchctl load /Library/LaunchDaemons/com.certbot.renew.plist
    ```

## Docker Setup (To Be Added)

### Development Environment

### Production Environment
