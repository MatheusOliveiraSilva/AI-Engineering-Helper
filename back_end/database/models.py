from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
import datetime

DATABASE_URL = "postgresql://matheus:password@localhost/users_chat_history"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    sub = Column(String(255), unique=True, index=True)  # ID do Auth0, que pode expirar
    email = Column(String(255), unique=True, index=True)  # e-mail único e permanente
    name = Column(String(255), nullable=True)
    picture = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class UserSession(Base):
    __tablename__ = "user_sessions"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relação para facilitar acesso ao usuário associado
    user = relationship("User", backref="sessions")

class ConversationThread(Base):
    __tablename__ = "conversation_threads"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), ForeignKey('user_sessions.session_id', ondelete='CASCADE'), nullable=False, index=True)
    thread_id = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)