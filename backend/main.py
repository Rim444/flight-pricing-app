from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
import jwt
from jwt import PyJWTError
from datetime import datetime, timedelta, timezone
from typing import Optional
import pandas as pd

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
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

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
    except PyJWTError:
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
    access_token = create_access_token(data={"sub": user.username}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username}

def load_data():
    forecast_url = "https://raw.githubusercontent.com/ВАШ_ЛОГИН/flight-pricing-app/main/seasonal_forecast.csv"
    try:
        df = pd.read_csv(forecast_url)
    except Exception:
        data = {
            "route": ["Moscow-Beijing", "Moscow-Paris", "Moscow-New York", "Moscow-Dubai", "Moscow-Istanbul"] * 6,
            "date": ["2026-06-01"] * 30,
            "seats": [150] * 30,
            "X_price": [25000, 30000, 45000, 35000, 28000] * 6,
            "X_price_demand": [0.5, 0.6, 0.7, 0.55, 0.65] * 6,
            "0.1_base_demand": [80, 60, 90, 70, 85] * 6,
            "0.2_base_demand": [90, 70, 100, 80, 95] * 6,
            "0.3_base_demand": [100, 80, 110, 90, 105] * 6,
            "0.4_base_demand": [110, 90, 120, 100, 115] * 6,
            "0.5_base_demand": [120, 95, 140, 110, 130] * 6,
            "0.6_base_demand": [130, 100, 150, 120, 140] * 6,
            "0.7_base_demand": [140, 110, 160, 130, 150] * 6,
            "0.8_base_demand": [150, 120, 170, 140, 160] * 6,
            "0.9_base_demand": [160, 130, 180, 150, 170] * 6
        }
        df = pd.DataFrame(data)
    return df

FORECAST_DF = load_data()

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
    
    row_data = row.iloc[0]
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