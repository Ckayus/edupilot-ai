
from pathlib import Path
import sqlite3
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, HTTPException

from pydantic import EmailStr
from fastapi import Depends
from pydantic import Field

from auth import (
    create_access_token,
    get_current_user,
    get_db as get_auth_db,
    hash_password,
    init_auth_db,
    verify_password,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="EduPilot AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = Path(__file__).with_name("edupilot.db")
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:1.5b"


def get_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                subject TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id)
                    REFERENCES conversations(id)
            )
        """)


init_db()
init_auth_db()


def now():
    return datetime.now(timezone.utc).isoformat()


class TutorRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    subject: str = Field(default="Auto-detect", max_length=100)
    conversation_id: str | None = None


class TutorResponse(BaseModel):
    answer: str
    subject: str
    conversation_id: str


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)


@app.get("/")
def home():
    return {"message": "Welcome to EduPilot AI"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}



@app.get("/api/conversations")
def list_conversations(
    current_user: dict = Depends(get_current_user),
):
    with get_db() as db:
        rows = db.execute("""
            SELECT id, title, subject, created_at, updated_at
            FROM conversations
            WHERE user_id = ?
            ORDER BY updated_at DESC
        """, (current_user["id"],)).fetchall()

    return [dict(row) for row in rows]




@app.get("/api/conversations/{conversation_id}")
def get_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    with get_db() as db:
        conversation = db.execute(
            """
            SELECT id, title, subject, created_at, updated_at
            FROM conversations
            WHERE id = ? AND user_id = ?
            """,
            (conversation_id, current_user["id"]),
        ).fetchone()

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found.",
            )

        messages = db.execute("""
            SELECT role, content, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
        """, (conversation_id,)).fetchall()

    return {
        "conversation": dict(conversation),
        "messages": [dict(message) for message in messages],
    }


async def detect_subject(question: str) -> str:
    prompt = (
        "Identify the main academic subject or field needed "
        "to answer the student's question.\n"
        "Examples: Biology, Chemistry, Physics, Mathematics, "
        "History, Economics, Geography, English, Programming, "
        "Computer Science, Business, or another suitable field.\n"
        "Return only the subject name. No explanation.\n\n"
        f"Student question: {question}"
    )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "stream": False,
                },
            )

            response.raise_for_status()
            result = response.json()["message"]["content"].strip()

            if not result:
                return "General"

            return result[:100]

    except (httpx.HTTPError, KeyError, ValueError):
        return "General"


@app.post("/api/tutor/chat", response_model=TutorResponse)
async def tutor_chat(
    request: TutorRequest,
    current_user: dict = Depends(get_current_user),
):
    conversation_id = request.conversation_id
    
    if request.subject.strip().lower() in ("", "auto-detect"):
        selected_subject = await detect_subject(request.question)
    else:
        selected_subject = request.subject.strip()
        
    with get_db() as db:
        if conversation_id:
            conversation = db.execute(
                "SELECT * FROM conversations WHERE id = ? AND user_id = ?",
                (conversation_id, current_user["id"]),
            ).fetchone()

            if conversation is None:
                raise HTTPException(
                    status_code=404,
                    detail="Conversation not found.",
                )

        else:
            conversation_id = str(uuid.uuid4())
            timestamp = now()

            db.execute("""
                INSERT INTO conversations
                (id, title, subject, created_at, updated_at, user_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                conversation_id,
                request.question[:60],
                selected_subject,
                timestamp,
                timestamp,
                current_user["id"],
            ))

        
        db.execute("""
            UPDATE conversations
            SET subject = ?, updated_at = ?
            WHERE id = ?
        """, (selected_subject, now(), conversation_id))


        # Load only the latest 10 messages for AI context.
        rows = db.execute("""
            SELECT role, content
            FROM (
                SELECT id, role, content
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id DESC
                LIMIT 10
            )
            ORDER BY id ASC
        """, (conversation_id,)).fetchall()

        history = [
            {"role": row["role"], "content": row["content"]}
            for row in rows
        ]

        db.execute("""
            UPDATE conversations
            SET updated_at = ?
            WHERE id = ?
        """, (now(), conversation_id))

    
        messages = [
            {
                "role": "system",
                "content": (
                    "You are EduPilot AI, an intelligent, friendly, and patient personal tutor. "
                    f"You are currently teaching {selected_subject}. "

                    "Your responsibilities are: "
                    "1. Explain concepts clearly using simple language. "
                    "2. Break difficult topics into smaller steps. "
                    "3. Give practical, relevant examples. "
                    "4. Use exercises where appropriate. "
                    "5. Encourage students to think critically rather than simply memorising. "
                    "6. Correct mistakes politely and explain why they are mistakes. "
                    "7. Adapt explanations to the student's level. "

                    "For Mathematics, show calculations and explain each step. "
                    "For Science, explain principles and use real-world examples. "
                    "For English, help with grammar, vocabulary, comprehension, and writing. "
                    "For Python, provide readable code examples and explain how they work. "

                    "Never assume the student understands a concept without explanation. "
                    "Be accurate, supportive, and educational."
                ),
            },
        ]


    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "messages": messages,
                    "stream": False,
                },
            )
            response.raise_for_status()
            answer = response.json()["message"]["content"]

    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Ollama is unavailable. Make sure it is running.",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="The AI took too long to respond.",
        )
    except httpx.HTTPStatusError:
        raise HTTPException(
            status_code=502,
            detail="Ollama returned an error. Check the model.",
        )
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=502,
            detail="The AI returned an unexpected response.",
        )

    with get_db() as db:
        db.execute("""
            INSERT INTO messages
            (conversation_id, role, content, created_at)
            VALUES (?, 'assistant', ?, ?)
        """, (conversation_id, answer, now()))

        db.execute("""
            UPDATE conversations
            SET updated_at = ?
            WHERE id = ?
        """, (now(), conversation_id))

    return TutorResponse(
        answer=answer,
        subject=selected_subject,
        conversation_id=conversation_id,
    )
#  REGISTRATION AND LOGIN ENDPOINTS


@app.post("/api/auth/register")
def register_student(request: RegisterRequest):
    email = request.email.strip().lower()

    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise HTTPException(
            status_code=400,
            detail="Please enter a valid email address.",
        )

    user_id = str(uuid.uuid4())
    timestamp = now()
    password_hash = hash_password(request.password)

    try:
        with get_auth_db() as db:
            db.execute(
                """
                INSERT INTO users (id, email, password_hash, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, email, password_hash, timestamp),
            )
    except Exception as exc:
        import sqlite3

        if isinstance(exc, sqlite3.IntegrityError):
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists.",
            )
        raise

    return {
        "message": "Account created successfully.",
        "user_id": user_id,
        "email": email,
    }


@app.post("/api/auth/login")
def login_student(request: LoginRequest):
    email = request.email.strip().lower()

    with get_auth_db() as db:
        user = db.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,),
        ).fetchone()

    if user is None or not verify_password(
        request.password,
        user["password_hash"],
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password.",
        )

    token = create_access_token(user["id"])

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
        },
    }
