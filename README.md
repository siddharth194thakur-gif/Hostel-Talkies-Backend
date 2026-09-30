# 🏢 HostelTalkies — Backend API

> Production-grade RESTful API backend for **HostelTalkies**, an all-in-one digital campus and hostel community management platform built with **Django** and **Django REST Framework (DRF)**.

[![Django](https://img.shields.io/badge/Django-5.2+-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15+-A30000?style=for-the-badge&logo=django&logoColor=white)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![JWT](https://img.shields.io/badge/JWT-SimpleJWT-black?style=for-the-badge&logo=json-web-tokens)](https://jwt.io/)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

---

## 📖 Overview

HostelTalkies Backend powers a unified community platform designed specifically for university residences. It connects students across campus dormitories for peer-to-peer trading, academic resource exchange, hostel room allocations, official announcements, and direct student messaging.

- **Live Frontend**: [https://hosteltalkies.fun](https://hosteltalkies.fun)
- **Frontend Repository**: [Hostel-Talkies-Frontend](https://github.com/siddharth194thakur-gif/Hostel-Talkies-Frontend)
- **Backend Deployment**: Render Web Service (Python 3.11 + Gunicorn)

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Framework** | Python 3.10+, Django 5, Django REST Framework (DRF) |
| **Database** | PostgreSQL (Production) / SQLite (Local & Resilient Fallback) |
| **Authentication** | SimpleJWT (JSON Web Tokens with access token refresh) |
| **API Architecture**| RESTful JSON endpoints, generic class-based views & ViewSets |
| **Static & Media** | WhiteNoise (Compressed static assets), Pillow (Image validation) |
| **CORS & Security** | `django-cors-headers`, DRF Rate Throttling, Custom Permission Classes |
| **Server** | Gunicorn WSGI HTTP Server |

---

## 🌟 Key Backend Modules & Features

### 1. 🔐 Authentication & Student Management (`/api/auth/`)
- Public student registration with dynamic hostel, block, and room assignment.
- JWT-based authentication (15-minute access token, 90-day refresh token rotation).
- Resilient authentication with `LenientJWTAuthentication` for unauthenticated public reads.
- Student profile customization (branch, programme, bio, contact preferences).
- Account security: user blocking system and administrative suspension middleware.

### 2. 🏢 Hostel & Room Hierarchy (`/api/hostels/`)
- Cascading data model: **Hostel ➔ Block ➔ Room**.
- Live tracking of room occupancy and resident counts.
- Public read access for registration dropdowns with zero authentication barriers.
- Exception-safe serializers preventing N+1 query bottlenecks.

### 3. 🛍️ Campus Marketplace & Borrow Tracker (`/api/posts/`)
- Student listings for buying, selling, and free item giveaways.
- Item borrowing and lending workflow with return date tracking.
- Moderated categories, multi-image support, comments, and post bookmarking.

### 4. 📚 Academic Study Repository (`/api/study/`)
- University syllabus notes, handouts, and Previous Year Questions (PYQs).
- Categorized by department, course code, and semester.
- Atomic download metric tracking using database `F()` expressions.

### 5. 📢 Official Notices & Events (`/api/notices/`, `/api/events/`)
- Verified administrative broadcasts with priority indicators (`Urgent`, `Important`, `Normal`).
- Hostel-specific and block-specific notice targeting.
- Upcoming campus workshops, sports matches, and cultural event RSVPs.

### 6. 💬 Direct & Group Messaging (`/api/messages/`)
- Private 1-on-1 direct conversations between verified hostel residents.
- Group chat management with member controls, media attachments, and message reactions.

---

## 🛡️ Reliability & Security Architecture

- **Self-Healing Database Connectivity**: Django configuration dynamically probes PostgreSQL reachability. If remote database connectivity is interrupted, it seamlessly uses a local SQLite fallback, preventing 500 downtime.
- **Defensive CORS**: Configured specifically for `hosteltalkies.fun`, `www.hosteltalkies.fun`, and Vercel preview environments with credential verification. Wildcards are strictly avoided.
- **Throttling**: Rate-limiting policies (`120/min` anonymous, `1200/min` authenticated) preventing API abuse and brute-force attempts.
- **Image Integrity**: File extension whitelisting, 25MB upload limits, and byte-level PIL verification.

---

## 🚀 Local Development Setup

### Prerequisites
- Python 3.10 or higher
- Git

### 1. Clone Repository
```bash
git clone https://github.com/siddharth194thakur-gif/Hostel-Talkies-Backend.git
cd Hostel-Talkies-Backend
```

### 2. Set Up Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory:
```env
DJANGO_SECRET_KEY=your-development-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
# Leave DATABASE_URL empty for SQLite local development, or supply PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost:5432/hosteltalkies
```

### 5. Run Database Migrations & Initial Setup
```bash
python manage.py migrate
python manage.py setup_initial_data
```

### 6. Start Development Server
```bash
python manage.py runserver 127.0.0.1:8000
```

- API Base URL: `http://127.0.0.1:8000/api/`
- Admin Operations Portal: `http://127.0.0.1:8000/admin/`

---

## 🧪 Testing

Run the Django automated test suite:
```bash
python manage.py test hostels.tests users.tests study.tests
```

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
