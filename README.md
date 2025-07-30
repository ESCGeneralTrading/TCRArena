# TCRArena
# 🏟️ TCR Arena – Sports, Collectibles & Culture

**TCR Arena** is a Flask-based web platform that brings together sports news, memorabilia history, video content, and user engagement — all in one place.

---

## 🚀 Features

- 📰 News & Blogs with category filtering and full-page views
- 📺 Dynamic YouTube Video integration (@TheCollectRoom)
- 🛍️ Memorabilia Product Showcase
- 📜 Memorabilia history 
- 📬 “Join Free” Pop-up Form to Access Premium Content
- 📱 Responsive Layout with Custom Styling

---

## 🛠️ Tech Stack

- **Backend:** Python (Flask)
- **Frontend:** HTML, CSS, Jinja2
- **Database:** SQLite (Dev) / PostgreSQL (Production)
- **Admin:** Flask-Login + Flask-Admin
- **Hosting:** Render / Hostinger (Custom Domain)
- **API:** YouTube Data API, Live Sports Scores API

---

## ⚙️ Installation (Local Setup)

```bash
git clone https://github.com/yourusername/tcr-arena.git
cd tcr-arena
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
flask db upgrade
