import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from .database import Base

class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

class CaseModel(Base):
    __tablename__ = "cases"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="Open") # Open / Under Investigation / Closed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    evidence = relationship("EvidenceModel", back_populates="case", cascade="all, delete-orphan")
    findings = relationship("FindingModel", back_populates="case_ref", cascade="all, delete-orphan")
    iocs = relationship("IOCModel", back_populates="case", cascade="all, delete-orphan")

class EvidenceModel(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    sha256_hash = Column(String, unique=True, index=True, nullable=False)
    metadata_info = Column(Text, nullable=True)
    upload_timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    case = relationship("CaseModel", back_populates="evidence")

class FindingModel(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    finding_type = Column(String, nullable=False) # Normal / Suspicious / Critical
    description =Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    case_ref = relationship("CaseModel", back_populates="findings")

class IOCModel(Base):
    __tablename__ = "iocs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    ioc_value = Column(String, index=True, nullable=False)
    type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    source = Column(String, nullable=True)
    reason = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    case = relationship("CaseModel", back_populates="iocs")