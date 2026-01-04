

# Setup and Deployment Guide

## Quick Start

```bash
git clone <your-repo>
cd VR-project

cp .env.example .env
nano .env

docker compose up --build
```

After startup:

* Frontend: [http://localhost:8080](http://localhost:8080)
* Backend API: [http://localhost:8000](http://localhost:8000)

---

## Requirements

* Docker 20 or newer
* Docker Compose v2

No local installation of Python, Node.js, or Nginx is required.

---

## Environment Configuration

All environment-specific and sensitive configuration is stored in `.env`.

### `.env.example`

```env
# Security
SECRET_KEY=CHANGE_ME_SUPER_SECRET
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_HOURS=1

# Admin user (optional)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

# Database
DATA_DIR=./data
DATABASE_URL=sqlite:///./data/conversations.db

# Cookies
COOKIE_SECURE=false
COOKIE_SAMESITE=lax

# CORS
CORS_ORIGINS=http://localhost:8080

# Frontend (public)
API_BASE_URL=http://localhost:8000
```

Copy this file to `.env` and adjust values as needed.

---

## Important Environment Variables

### SECRET_KEY

Used to sign authentication cookies (JWT).

Must be changed before deployment.

Generate a secure value with:

```bash
openssl rand -hex 32
```

---

### Cookie Settings

| Variable        | Description                                 |
| --------------- | ------------------------------------------- |
| COOKIE_SECURE   | true for HTTPS, false for local development |
| COOKIE_SAMESITE | lax is recommended                          |

---

### API_BASE_URL

Public backend URL used by the frontend.
This value is not secret.

Examples:

```env
API_BASE_URL=http://localhost:8000
API_BASE_URL=https://api.example.com
```

---
Below is a **simple, explicit section** you can **add at the end of your README**.
It clearly tells people **what file to open and exactly what to change**, without introducing new concepts.

You can paste this **as-is**.

---

## Manual Frontend URL Update (Required)

The frontend HTML files contain **hardcoded backend URLs** by default.
When deploying this project, **you must update these URLs** to match your own backend domain.

### Files that must be edited

Open the following files:

* `frontend/index.html`
* `frontend/login.html`

---

### What to change

#### In `frontend/index.html`

Find this line:

```javascript
https://apivr.xxx.com/conversations/${convoId}/messages
```

Replace it with your backend API URL, for example:

```javascript
https://api.example.com/conversations/${convoId}/messages
```

---

#### In `frontend/login.html`

Find this line:

```javascript
https://apivr.xxx.com/login
```

Replace it with your backend API URL, for example:


```javascript
https://api.example.com/login
```


This step is required for every new deployment or fork of the project.

## Docker Compose

### docker-compose.yml

```yaml
services:
  backend:
    build: ./backend
    container_name: conversation-backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend/data:/app/data
    env_file:
      - .env

  frontend:
    build: ./frontend
    container_name: conversation-frontend
    ports:
      - "8080:80"
    depends_on:
      - backend
    env_file:
      - .env
```

This configuration:

* Runs the backend on port 8000
* Runs the frontend on port 8080
* Stores database data in `backend/data/`
* Injects `.env` into both containers

---

## Authentication Flow

1. User logs in via `login.html`
2. Backend sets an HTTP-only authentication cookie
3. Frontend sends requests with `credentials: include`
4. Backend validates the JWT on every request

No tokens are stored in localStorage.

---

## Local Development Configuration

```env
COOKIE_SECURE=false
API_BASE_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:8080
```

Start services with:

```bash
docker compose up --build
```

---

## Production Configuration (HTTPS)

```env
COOKIE_SECURE=true
API_BASE_URL=https://api.yourdomain.com
CORS_ORIGINS=https://yourdomain.com
```

---

# Cloudflare Zero Trust Setup

## Prerequisites

* A domain managed by Cloudflare
* Cloudflare Zero Trust enabled
* Docker services running on a public server
* Ports 80 and 443 accessible from Cloudflare

---

## Create Cloudflare Tunnel

On the server:

```bash
cloudflared tunnel login
cloudflared tunnel create conversation-app
```

---

## Configure Tunnel Routing

Create `cloudflared/config.yml`:

```yaml
tunnel: conversation-app
credentials-file: /root/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: app.example.com
    service: http://localhost:8080

  - hostname: api.example.com
    service: http://localhost:8000

  - service: http_status:404
```

Start the tunnel:

```bash
cloudflared tunnel run conversation-app
```

---

## Protect Frontend with Cloudflare Access

1. Open Cloudflare Dashboard
2. Go to Zero Trust → Access → Applications
3. Add a Self-hosted application
4. Set domain to `app.example.com`
5. Configure an access policy (email domain or specific users)

This protects the frontend before any application code is reached.

---

## Protect Backend API with Cloudflare Access

1. Add a second Self-hosted application
2. Set domain to `api.example.com`
3. Apply an access policy

This prevents direct API access outside Cloudflare.

---

## Production Environment Values with Cloudflare

```env
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
API_BASE_URL=https://api.example.com
CORS_ORIGINS=https://app.example.com
```

---

## Local Development Without Cloudflare

Cloudflare is not required for local development.

```env
COOKIE_SECURE=false
API_BASE_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:8080
```

Run normally with:

```bash
docker compose up --build
```

---

