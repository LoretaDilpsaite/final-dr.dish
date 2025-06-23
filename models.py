from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
from .utils.crypto import encrypt_value, decrypt_value

Base = declarative_base()

class OAuth2Client(Base):
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True)
    client_id = Column(String(48), unique=True, nullable=False)
    _client_secret = Column("client_secret", String(255), nullable=False)
    redirect_uris = Column(String(255), nullable=False)
    scope = Column(String(255), default='')

    @hybrid_property
    def client_secret(self):
        return decrypt_value(self._client_secret)

    @client_secret.setter
    def client_secret(self, plaintext):
        self._client_secret = encrypt_value(plaintext)

class OAuth2Token(Base):
    __tablename__ = 'tokens'
    id = Column(Integer, primary_key=True)
    client_id = Column(String(48))
    user_id = Column(Integer)
    access_token = Column(String(255), unique=True)
    refresh_token = Column(String(255), unique=True)
    scope = Column(String(255))
    expires_at = Column(Integer)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    role = Column(String, default="nurse")

class PatientConsent(Base):
    __tablename__ = 'patient_consents'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    data_type = Column(String)
    consent_given = Column(Boolean)
    timestamp = Column(DateTime, default=datetime.utcnow)

