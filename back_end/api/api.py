import os
import uuid
import datetime
from typing import List, Tuple
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Depends, Response, Request
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth

from back_end.database.models import (
    User, UserSession, ConversationThread, SessionLocal, init_db
)

load_dotenv(dotenv_path=".env")

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("MIDDLEWARE_SECRET_KEY"))

init_db()

oauth = OAuth()
auth0 = oauth.register(
    name='auth0',
    client_id=os.getenv("AUTH0_CLIENT_ID"),
    client_secret=os.getenv("AUTH0_CLIENT_SECRET"),
    server_metadata_url=f"https://{os.getenv('AUTH0_DOMAIN')}/.well-known/openid-configuration",
    client_kwargs={'scope': 'openid profile email'},
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------------------------------------------------------
# 1) Login and Session Management Endpoints
# -------------------------------------------------------------------
@app.get("/auth/login")
async def auth_login(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await auth0.authorize_redirect(request, redirect_uri)

@app.get("/auth/callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await auth0.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Falha na autenticação.") from e

    user_info = token.get("userinfo")
    if not user_info:
        raise HTTPException(status_code=400, detail="Não foi possível obter dados do usuário.")

    email = user_info.get("email")
    sub = user_info.get("sub")
    if not email or not sub:
        raise HTTPException(status_code=400, detail="Dados insuficientes para autenticação.")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            sub=sub,
            name=user_info.get("name"),
            picture=user_info.get("picture")
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.sub = sub
        db.commit()

    session_token = str(uuid.uuid4())
    new_session = UserSession(session_id=session_token, user_id=user.id)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    response = RedirectResponse(url="http://localhost:8501")
    response.set_cookie(
        key="sub",
        value=sub,
        max_age=30 * 24 * 3600,
        httponly=False,
        samesite="lax",
        secure=False,
        domain="localhost",
        path="/"
    )
    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=30 * 24 * 3600,
        httponly=False,
        samesite="lax",
        secure=False,
        domain="localhost",
        path="/"
    )
    return response

@app.get("/test/set-cookie")
def set_cookie_test(response: Response):
    test_value = "auth0|teste123"
    response.set_cookie(
        key="sub",
        value=test_value,
        max_age=30 * 24 * 3600,
        httponly=False,
        samesite="lax",
        secure=False,
        domain="localhost",
        path="/"
    )
    return {"message": f"Cookie 'sub' set to {test_value}"}

# -------------------------------------------------------------------
# 2) BaseModels to chat history creation
# -------------------------------------------------------------------
class ConversationCreate(BaseModel):
    session_id: str
    thread_id: str
    first_message_role: str = "user"
    first_message_content: str

class ConversationUpdate(BaseModel):
    thread_id: str
    # We defined that "messages" is a list of lists [role, content],
    messages: List[List[str, str]]

# -------------------------------------------------------------------
# 3) Session Creating/Updating Endpoints
# -------------------------------------------------------------------
@app.post("/session")
def create_session(response: Response, db: Session = Depends(get_db)):
    session_token = str(uuid.uuid4())
    new_session = UserSession(session_id=session_token)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    response.set_cookie(key="session_token", value=session_token)
    return {"session_id": session_token, "created_at": new_session.created_at}

@app.get("/session")
def get_session(session_token: str, db: Session = Depends(get_db)):
    session_obj = db.query(UserSession).filter(UserSession.session_id == session_token).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session_obj.session_id,
        "user_id": session_obj.user_id,
        "created_at": session_obj.created_at
    }

# -------------------------------------------------------------------
# 4) Chat Creating/Updating Endpoints
# -------------------------------------------------------------------
@app.post("/conversation")
def add_conversation(data: ConversationCreate, db: Session = Depends(get_db)):
    """
    Create a new conversation thread in the database and save the first message.
    """
    session_obj = db.query(UserSession).filter(UserSession.session_id == data.session_id).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")

    initial_messages = [(data.first_message_role, data.first_message_content)]

    new_conv = ConversationThread(
        session_id=data.session_id,
        thread_id=data.thread_id,
        messages=initial_messages,
        created_at=datetime.datetime.utcnow(),
        last_used=datetime.datetime.utcnow()
    )
    db.add(new_conv)
    db.commit()
    db.refresh(new_conv)
    return {
        "id": new_conv.id,
        "session_id": new_conv.session_id,
        "thread_id": new_conv.thread_id,
        "messages": new_conv.messages,
        "created_at": new_conv.created_at,
        "last_used": new_conv.last_used
    }

@app.patch("/conversation")
def update_conversation(data: ConversationUpdate, db: Session = Depends(get_db)):
    """
    Update chat history in database with the new messages.
    """
    conversation = db.query(ConversationThread).filter(
        ConversationThread.thread_id == data.thread_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation.messages = data.messages
    conversation.last_used = datetime.datetime.utcnow()

    db.commit()
    db.refresh(conversation)
    return {
        "id": conversation.id,
        "thread_id": conversation.thread_id,
        "messages": conversation.messages,
        "session_id": conversation.session_id,
        "created_at": conversation.created_at,
        "last_used": conversation.last_used
    }

@app.get("/conversation")
def get_conversations(session_token: str, db: Session = Depends(get_db)):
    convs = db.query(ConversationThread).filter(
        ConversationThread.session_id == session_token
    ).order_by(ConversationThread.created_at.asc()).all()

    return {
        "conversations": [
            {
                "id": conv.id,
                "session_id": conv.session_id,
                "thread_id": conv.thread_id,
                "messages": conv.messages,
                "created_at": conv.created_at,
                "last_used": conv.last_used
            }
            for conv in convs
        ]
    }


