from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pandas as pd, sqlite3, hashlib, jwt, os, urllib.request
from pathlib import Path
from datetime import datetime, timedelta, timezone

SECRET = "k-12345"; ALG = "HS256"; EXP = 60
QS = ["0.1","0.2","0.3","0.4","0.5","0.6","0.7","0.8","0.9"]

BASE = Path(__file__).resolve().parent.parent

def find_file(names, roots):
    for r in roots:
        for n in names:
            p = r / n
            if p.exists():
                return p
    return None

def find_dir(names, roots):
    for r in roots:
        for n in names:
            p = r / n
            if p.is_dir():
                return p
    return None

DATA_ROOTS = [BASE / "data", Path.cwd() / "data", Path.cwd()]
FRONT_ROOTS = [BASE, Path.cwd()]

fc_path = find_file(["my_forecast.csv"], DATA_ROOTS)
if fc_path is None:
    sp = find_file(["seasonal_forecast.csv"], DATA_ROOTS)
    if sp is None:
        os.makedirs(DATA_ROOTS[0], exist_ok=True)
        urllib.request.urlretrieve(
            "https://gist.githubusercontent.com/Murkat-git/3ddc868889d3e0d37542d786c8b1aa74/raw/seasonal_forecast.csv",
            DATA_ROOTS[0] / "seasonal_forecast.csv")
        sp = DATA_ROOTS[0] / "seasonal_forecast.csv"
    fc_path = sp

rt_path = find_file(["routes.csv"], DATA_ROOTS)
if rt_path is None:
    os.makedirs(DATA_ROOTS[0], exist_ok=True)
    rt_path = DATA_ROOTS[0] / "routes.csv"
    urllib.request.urlretrieve(
        "https://gist.githubusercontent.com/Murkat-git/3ddc868889d3e0d37542d786c8b1aa74/raw/a934b1220da2b20d7f3eb397a7459fe78ea168ef/routes.csv",
        rt_path)

df = pd.read_csv(fc_path)
rt = pd.read_csv(rt_path)

def pick(cols, keys):
    cl = [str(c).lower() for c in cols]
    for k in keys:
        for i, c in enumerate(cl):
            if k in c:
                return cols[i]
    return None

base_col = pick(rt.columns, ["base_price", "base"])
sens_col = pick(rt.columns, ["price_sensitivity", "sensitivity", "sens", "slope"])
meta = {}
for _, r in rt.iterrows():
    try:
        meta[str(r["route"])] = (float(r[base_col]), float(r[sens_col]))
    except Exception:
        pass

front_dir = find_dir(["docs", "frontend", "static"], FRONT_ROOTS)

DB_PATH = "users.db"
def h(p): return hashlib.sha256(str(p).encode()).hexdigest()
def db_init():
    c = sqlite3.connect(DB_PATH); cur = c.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)")
    cur.execute("SELECT 1 FROM users WHERE username='admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("admin", h("123456")))
    c.commit(); c.close()
db_init()

def tok(u):
    e = datetime.now(timezone.utc) + timedelta(minutes=EXP)
    return jwt.encode({"sub": u, "exp": e}, SECRET, algorithm=ALG)
def who(auth):
    if not auth or not str(auth).startswith("Bearer "):
        raise HTTPException(401, "Нет токена")
    try:
        u = jwt.decode(str(auth)[7:], SECRET, algorithms=[ALG])["sub"]
    except Exception:
        raise HTTPException(401, "Токен протух или неверный")
    c = sqlite3.connect(DB_PATH); cur = c.cursor()
    cur.execute("SELECT 1 FROM users WHERE username=?", (u,)); ok = cur.fetchone(); c.close()
    if not ok: raise HTTPException(401, "Пользователь не найден")
    return u

class Auth(BaseModel):
    username: str; password: str

app = FastAPI()

@app.get("/api/health")
def health():
    return {"status": "ok", "forecast_rows": int(len(df)),
            "forecast_cols": [str(c) for c in df.columns],
            "routes_cols": [str(c) for c in rt.columns],
            "base_col": base_col, "sens_col": sens_col,
            "routes": sorted(set(str(x) for x in df["route"].unique())),
            "front_dir": str(front_dir), "forecast_file": str(fc_path)}

@app.post("/register")
def register(a: Auth):
    if len(a.username) < 3 or len(a.password) < 6:
        raise HTTPException(400, "Логин от 3 символов, пароль от 6")
    c = sqlite3.connect(DB_PATH); cur = c.cursor()
    try:
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (a.username, h(a.password)))
        c.commit()
    except sqlite3.IntegrityError:
        c.close(); raise HTTPException(400, "Пользователь уже существует")
    c.close(); return {"message": "OK"}

@app.post("/login")
def login(a: Auth):
    c = sqlite3.connect(DB_PATH); cur = c.cursor()
    cur.execute("SELECT password FROM users WHERE username=?", (a.username,)); row = cur.fetchone(); c.close()
    if not row or row[0] != h(a.password):
        raise HTTPException(401, "Неверный логин или пароль")
    return {"access_token": tok(a.username), "token_type": "bearer", "user": a.username}

@app.get("/api/routes")
def routes(authorization: str = None):
    who(authorization)
    out = []
    for r in sorted(set(str(x) for x in df["route"].unique())):
        bp = meta.get(r, (None, None))[0]
        out.append({"route": r, "base_price": bp})
    return out

@app.get("/api/calculate")
def calculate(route: str, date: str, price: float, authorization: str = None):
    who(authorization)
    row = df[(df["route"].astype(str) == route) & (df["date"].astype(str) == date)]
    if row.empty:
        raise HTTPException(404, "Рейс на эту дату не найден")
    row = row.iloc[0]
    seats = int(row["seats"])
    base, sens = meta.get(route, (float(row.get("0.5_price", 0)) or 0.0, 0.0))
    want = []
    for q in QS:
        col = f"{q}_base_demand"
        d = float(row[col]) - sens * (price - base)
        want.append(max(0, int(round(d))))
    median = want[4]
    sold = min(seats, median)
    return {"seats": seats, "base_price": base, "want": median,
            "sold": sold, "free": seats - sold, "quantiles": want, "labels": QS}

if front_dir is not None:
    app.mount("/", StaticFiles(directory=str(front_dir), html=True), name="fe")