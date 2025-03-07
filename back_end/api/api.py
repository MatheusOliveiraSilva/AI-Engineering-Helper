import os
import uuid
from fastapi import FastAPI, HTTPException, Depends, Response, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from back_end.database.models import User, UserSession, ConversationThread, SessionLocal, init_db

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
        # Create a new user
        user = User(email=email, sub=sub, name=user_info.get("name"), picture=user_info.get("picture"))
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # If user is already in database, just update the sub (session cookie)
        user.sub = sub
        db.commit()

    # Create a new session id for user. This will be used as session cookie
    session_token = str(uuid.uuid4())
    new_session = UserSession(session_id=session_token, user_id=user.id)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    # Send to main page with cookies set
    response = RedirectResponse(url="http://localhost:8501")
    response.set_cookie(
        key="sub",
        value=sub,
        max_age=30 * 24 * 3600,   # 30 dias
        httponly=False,          # Para testes; em produção, considere usar True e validar no back-end
        samesite="lax",
        secure=False,            # Altere para True se usar HTTPS
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
        max_age=30 * 24 * 3600,  # 30 days
        httponly=False,
        samesite="lax",
        secure=False,
        domain="localhost",
        path="/"
    )
    return {"message": f"Cookie 'sub' set to {test_value}"}

# -------------------------------
#        Chat API
# -------------------------------

class ConversationCreate(BaseModel):
    session_id: str
    thread_id: str

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
    return {"session_id": session_obj.session_id, "user_id": session_obj.user_id, "created_at": session_obj.created_at}

@app.post("/conversation")
def add_conversation(conversation: ConversationCreate, db: Session = Depends(get_db)):
    session_obj = db.query(UserSession).filter(UserSession.session_id == conversation.session_id).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")
    new_conv = ConversationThread(session_id=conversation.session_id, thread_id=conversation.thread_id)
    db.add(new_conv)
    db.commit()
    db.refresh(new_conv)
    return {
        "id": new_conv.id,
        "session_id": new_conv.session_id,
        "thread_id": new_conv.thread_id,
        "created_at": new_conv.created_at,
    }

@app.get("/conversation")
def get_conversations(session_token: str, db: Session = Depends(get_db)):
    convs = db.query(ConversationThread).filter(ConversationThread.session_id == session_token).all()
    return {
        "conversations": [
            {
                "id": conv.id,
                "session_id": conv.session_id,
                "thread_id": conv.thread_id,
                "created_at": conv.created_at,
            }
            for conv in convs
        ]
    }
