from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel
import jwt
import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

SECRET_KEY = "your-secret-key-12345"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

SQLALCHEMY_DATABASE_URL = "sqlite:///./users.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

Base.metadata.create_all(bind=engine)

def get_password_hash(password: str):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str):
    return get_password_hash(plain_password) == hashed_password

# Инициализация admin ТОЛЬКО если его нет
def init_admin():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            db.add(User(username="admin", hashed_password=get_password_hash("123456")))
            db.commit()
    finally:
        db.close()

init_admin()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://rim444.github.io", "http://localhost:8000", "http://localhost:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AuthData(BaseModel):
    username: str
    password: str

@app.get("/")
def healthcheck():
    return {"status": "ok", "version": "7.0"}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user(db, username: str):
    return db.query(User).filter(User.username == username).first()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(OAuth2PasswordRequestForm), db: Session = Depends(get_db)):
    # Для простоты используем header-based auth вместо OAuth2 flow
    pass

@app.post("/register")
def register(data: AuthData, db: Session = Depends(get_db)):
    if len(data.username) < 3 or len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Логин от 3 символов, пароль от 6")
    if get_user(db, data.username):
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    
    db_user = User(username=data.username, hashed_password=get_password_hash(data.password))
    db.add(db_user)
    db.commit()
    return {"message": "User created successfully"}

@app.post("/login")
def login(data: AuthData, db: Session = Depends(get_db)):
    user = get_user(db, data.username)
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    
    access_token = create_access_token(data={"sub": user.username}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}

FORECAST_DATA = [
    {"route": "Moscow-Beijing", "date": "2026-06-01", "seats": 150, "X_price": 25000, "X_price_demand": 0.5, "0.1_base_demand": 80, "0.2_base_demand": 90, "0.3_base_demand": 100, "0.4_base_demand": 110, "0.5_base_demand": 120, "0.6_base_demand": 130, "0.7_base_demand": 140, "0.8_base_demand": 150, "0.9_base_demand": 160},
    {"route": "Moscow-Paris", "date": "2026-06-01", "seats": 150, "X_price": 30000, "X_price_demand": 0.6, "0.1_base_demand": 60, "0.2_base_demand": 70, "0.3_base_demand": 80, "0.4_base_demand": 90, "0.5_base_demand": 95, "0.6_base_demand": 100, "0.7_base_demand": 110, "0.8_base_demand": 120, "0.9_base_demand": 130},
    {"route": "Moscow-New York", "date": "2026-06-01", "seats": 150, "X_price": 45000, "X_price_demand": 0.7, "0.1_base_demand": 90, "0.2_base_demand": 100, "0.3_base_demand": 110, "0.4_base_demand": 120, "0.5_base_demand": 140, "0.6_base_demand": 150, "0.7_base_demand": 160, "0.8_base_demand": 170, "0.9_base_demand": 180},
    {"route": "Moscow-Dubai", "date": "2026-06-01", "seats": 150, "X_price": 35000, "X_price_demand": 0.55, "0.1_base_demand": 70, "0.2_base_demand": 80, "0.3_base_demand": 90, "0.4_base_demand": 100, "0.5_base_demand": 110, "0.6_base_demand": 120, "0.7_base_demand": 130, "0.8_base_demand": 140, "0.9_base_demand": 150},
    {"route": "Moscow-Istanbul", "date": "2026-06-01", "seats": 150, "X_price": 28000, "X_price_demand": 0.65, "0.1_base_demand": 85, "0.2_base_demand": 95, "0.3_base_demand": 105, "0.4_base_demand": 115, "0.5_base_demand": 130, "0.6_base_demand": 140, "0.7_base_demand": 150, "0.8_base_demand": 160, "0.9_base_demand": 170},
]

async def get_current_user_from_header(authorization: str = None, db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Не авторизован")
    
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Невалидный токен")
    except Exception:
        raise HTTPException(status_code=401, detail="Невалидный токен")
    
    user = get_user(db, username=username)
    if user is None:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user

@app.get("/api/calculate")
async def calculate(route: str, date: str, price: float, authorization: str = None, db: Session = Depends(get_db)):
    current_user = await get_current_user_from_header(authorization, db)
    
    row_data = next((item for item in FORECAST_DATA if item["route"] == route and item["date"] == date), None)
    if not row_data:
        raise HTTPException(status_code=404, detail="Route or date not found")
    
    seats = int(row_data["seats"])
    base_price = float(row_data["X_price"])
    sensitivity = float(row_data["X_price_demand"])
    median_demand = float(row_data["0.5_base_demand"])
    
    желают = median_demand - sensitivity * (price - base_price)
    купят = min(seats, max(0, int(желают)))
    quantiles = [max(0, int(float(row_data[f"{q}_base_demand"]) - sensitivity * (price - base_price))) for q in ["0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9"]]
    
    return {
        "total_seats": seats,
        "want_to_buy": max(0, int(желают)),
        "sold": купят,
        "remaining": seats - купят,
        "quantiles": quantiles
    }