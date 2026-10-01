from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from .config import settings
from .database import Base, engine
from .routers import auth, food, map, notifications, requests, deliveries, admin, dashboard

Base.metadata.create_all(bind=engine)

app=FastAPI(title="Aahar API",version="1.0.0",description="Smart Surplus Food Redistribution Platform API")
origins=[x.strip() for x in settings.CORS_ORIGINS.split(",") if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

app.include_router(auth.router,prefix="/api")
app.include_router(food.router,prefix="/api")
app.include_router(map.router,prefix="/api")
app.include_router(notifications.router,prefix="/api")
app.include_router(requests.router,prefix="/api")
app.include_router(deliveries.router,prefix="/api")
app.include_router(admin.router,prefix="/api")
app.include_router(dashboard.router,prefix="/api")

@app.get("/")
def root(): return {"name":"Aahar API","status":"running"}

@app.get("/api/health")
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status":"ok","database":"connected"}
