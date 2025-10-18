from sqlalchemy import create_engine, Column, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta, timezone
import uuid

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./mshield.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# East Africa Time (UTC+3)
EAT = timezone(timedelta(hours=3))
def now_eat():
    return datetime.now(EAT)

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=now_eat)
    is_active = Column(Boolean, default=True)
    payhero_account_id = Column(String, nullable=True)
    
    # Relationships
    savings_goals = relationship("SavingsGoal", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
    loans = relationship("Loan", back_populates="user")

class SavingsGoal(Base):
    __tablename__ = "savings_goals"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    goal_name = Column(String, nullable=False)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0.0)
    target_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_eat)
    
    # Relationships
    user = relationship("User", back_populates="savings_goals")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String, nullable=False)  # 'savings', 'loan', 'repayment'
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    timestamp = Column(DateTime, default=now_eat)
    payhero_transaction_id = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="transactions")

class Loan(Base):
    __tablename__ = "loans"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String, default="active")  # 'active', 'completed', 'defaulted'
    interest_rate = Column(Float, default=0.05)  # 5% interest
    due_date = Column(DateTime, nullable=False)
    repaid_amount = Column(Float, default=0.0)
    ai_category = Column(String, nullable=True)
    ai_confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=now_eat)
    
    # Relationships
    user = relationship("User", back_populates="loans")
    repayment_schedules = relationship("RepaymentSchedule", back_populates="loan")

class RepaymentSchedule(Base):
    __tablename__ = "repayment_schedules"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    loan_id = Column(String, ForeignKey("loans.id"), nullable=False)
    installment_amount = Column(Float, nullable=False)
    due_date = Column(DateTime, nullable=False)
    status = Column(String, default="pending")  # 'pending', 'paid', 'overdue'
    paid_at = Column(DateTime, nullable=True)
    
    # Relationships
    loan = relationship("Loan", back_populates="repayment_schedules")

# Create tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()