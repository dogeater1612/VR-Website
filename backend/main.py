from fastapi import FastAPI, HTTPException, Depends, Response, Cookie
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

from sqlalchemy import (
    create_engine, Column, Integer, String, Text,
    DateTime, ForeignKey, asc
)
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError

# =========================
# CONFIG (ENV ONLY)
# =========================

DATA_DIR = os.getenv("DATA_DIR", "./data")
os.makedirs(DATA_DIR, exist_ok=True)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DATA_DIR}/conversations.db"
)

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be set in .env")

ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", "1"))

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() == "true"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "").split(",")
    if o.strip()
]

# =========================
# DATABASE
# =========================

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =========================
# MODELS
# =========================

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password_hash = Column(String)

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(String(20))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# =========================
# SECURITY
# =========================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# =========================
# APP
# =========================

app = FastAPI()

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        print("ADMIN credentials not set → admin user NOT created")
        return

    db = SessionLocal()
    try:
        if not db.query(User).filter_by(username=ADMIN_USERNAME).first():
            db.add(User(
                username=ADMIN_USERNAME,
                password_hash=pwd_context.hash(ADMIN_PASSWORD)
            ))
            db.commit()
            print(f"Admin user '{ADMIN_USERNAME}' created")
    finally:
        db.close()

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# SCHEMAS
# =========================

class MessageCreate(BaseModel):
    role: str
    content: str

class LoginRequest(BaseModel):
    username: str
    password: str

# =========================
# AUTH
# =========================

def require_login(session: str = Cookie(None)):
    if not session:
        raise HTTPException(status_code=401)

    try:
        jwt.decode(session, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401)

# =========================
# ROUTES
# =========================

@app.post("/login")
def login(data: LoginRequest, response: Response, db=Depends(get_db)):
    user = db.query(User).filter_by(username=data.username).first()

    if not user or not pwd_context.verify(data.password, user.password_hash):
        raise HTTPException(status_code=401)

    token = jwt.encode(
        {
            "sub": user.username,
            "exp": datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
        path="/",
    )

    return {"status": "ok"}

@app.get("/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: int,
    _=Depends(require_login),
    db=Depends(get_db),
):
    msgs = (
        db.query(Message)
        .filter_by(conversation_id=conversation_id)
        .order_by(asc(Message.created_at))
        .all()
    )

    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at,
        }
        for m in msgs
    ]

@app.post("/conversations/{conversation_id}/messages")
def post_message(
    conversation_id: int,
    message: MessageCreate,
    db=Depends(get_db),
):
    convo = db.query(Conversation).filter_by(id=conversation_id).first()
    if not convo:
        db.add(Conversation(id=conversation_id))
        db.commit()

    msg = Message(
        conversation_id=conversation_id,
        role=message.role,
        content=message.content,
    )

    db.add(msg)
    db.commit()
    db.refresh(msg)

    return {
        "id": msg.id,
        "conversation_id": msg.conversation_id,
        "role": msg.role,
        "content": msg.content,
        "created_at": msg.created_at,
    }
