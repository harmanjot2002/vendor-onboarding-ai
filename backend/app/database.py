import os
import datetime as dt

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vendor_onboarding.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Run(Base):
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True)
    scenario_key = Column(String, nullable=True)
    vendor_name = Column(String, nullable=False)
    submitted_at = Column(DateTime, default=dt.datetime.utcnow)
    status = Column(String, default="running")  # running | approved | pending | rejected
    routing = Column(String, default="procurement")  # procurement | internal_audit
    reason_summary = Column(Text, default="")
    submission_json = Column(Text, default="{}")

    stages = relationship("RunStage", back_populates="run", order_by="RunStage.order_index")


class RunStage(Base):
    __tablename__ = "run_stages"

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("runs.id"))
    order_index = Column(Integer)
    stage_name = Column(String)
    status = Column(String)  # passed | flagged | failed | skipped
    detail = Column(Text, default="")
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    run = relationship("Run", back_populates="stages")


def init_db():
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()
