from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
import os
import urllib.request

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

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db, username: str):
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(db, username=username)
    if user is None:
        raise credentials_exception
    return user

@app.post("/register")
def register(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    if get_user(db, form_data.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(form_data.password)
    db_user = User(username=form_data.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "User created successfully"}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username}

def load_data():
    forecast_url = "https://raw.githubusercontent.com/username/repo/main/seasonal_forecast.csv"
    routes_url = "https://raw.githubusercontent.com/username/repo/main/routes.csv"
    try:
        forecast_df = pd.read_csv(forecast_url)
        routes_df = pd.read_csv(routes_url)
    except Exception:
        forecast_df = pd.DataFrame({
            "route": ["Moscow-Beijing", "Moscow-Paris", "Moscow-New York", "Moscow-Dubai", "Moscow-Istanbul"] * 3,
            "date": ["2026-06-01", "2026-06-05", "2026-06-10", "2026-06-15", "2026-06-20",
                     "2026-06-08", "2026-06-12", "2026-06-18", "2026-06-22", "2026-06-25",
                     "2026-06-02", "2026-06-06", "2026-06-11", "2026-06-16", "2026-06-21"],
            "median_demand": [120, 95, 140, 110, 130, 115, 100, 135, 105, 125, 118, 98, 138, 108, 128],
            "base_price": [25000, 30000, 45000, 35000, 28000, 26000, 31000, 46000, 36000, 29000, 25500, 30500, 45500, 35500, 28500],
            "sensitivity": [0.5, 0.6, 0.7, 0.55, 0.65, 0.52, 0.62, 0.72, 0.57, 0.67, 0.51, 0.61, 0.71, 0.56, 0.66]
        })
        routes_df = pd.DataFrame({
            "route": ["Moscow-Beijing", "Moscow-Paris", "Moscow-New York", "Moscow-Dubai", "Moscow-Istanbul"],
            "total_seats": [150, 150, 150, 150, 150]
        })
    return forecast_df, routes_df

FORECAST_DF, ROUTES_DF = load_data()

@app.get("/api/calculate")
async def calculate(
    route: str,
    date: str,
    price: float,
    current_user: User = Depends(get_current_user)
):
    row = FORECAST_DF[(FORECAST_DF["route"] == route) & (FORECAST_DF["date"] == date)]
    if row.empty:
        raise HTTPException(status_code=404, detail="Route or date not found")
    
    median_demand = float(row.iloc[0]["median_demand"])
    base_price = float(row.iloc[0]["base_price"])
    sensitivity = float(row.iloc[0]["sensitivity"])
    
    route_info = ROUTES_DF[ROUTES_DF["route"] == route]
    total_seats = int(route_info.iloc[0]["total_seats"]) if not route_info.empty else 150
    
    желают = median_demand - sensitivity * (price - base_price)
    купят = min(total_seats, max(0, int(желают)))
    осталось = total_seats - купят
    
    return {
        "total_seats": total_seats,
        "want_to_buy": max(0, int(желают)),
        "sold": купят,
        "remaining": осталось
    }