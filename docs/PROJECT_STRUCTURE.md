# Project structure

frontend/
- src/App.jsx — website routes
- src/pages/ — all website screens
- src/components/ — reusable UI
- src/context/AuthContext.jsx — JWT session
- src/api.js — Axios API client
- tailwind.config.js — Aahar design system

backend/
- app/main.py — FastAPI app
- app/security.py — JWT + password hashing
- app/models/models.py — SQLAlchemy models
- app/schemas/ — Pydantic request/response models
- app/routers/auth.py — registration/login
- app/routers/food.py — food listing APIs
- app/routers/map.py — OSRM route API
- app/routers/notifications.py — notifications
- app/services/email.py — SMTP email helper

database/
- schema.sql — PostgreSQL tables and indexes
