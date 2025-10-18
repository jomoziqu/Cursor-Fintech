from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import uvicorn

# Import our modules
from database import get_db, create_tables, User, SavingsGoal, Transaction, Loan, RepaymentSchedule
from auth import get_password_hash, authenticate_user, create_access_token, get_current_user
from ai_classifier import classifier

# Create FastAPI app
app = FastAPI(title="M-Shield API", description="AI-Powered Financial Protection Platform")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],  # Be specific about allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Create database tables
create_tables()

# Pydantic models for API
class UserRegister(BaseModel):
    email: EmailStr
    phone: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class SavingsGoalCreate(BaseModel):
    goal_name: str
    target_amount: float
    target_date: datetime

class TransactionCreate(BaseModel):
    amount: float
    transaction_type: str
    description: Optional[str] = None
    goal_id: Optional[str] = None  # <-- Add goal_id

class LoanRequest(BaseModel):
    amount: float
    reason: str

class ClassificationRequest(BaseModel):
    description: str

# East Africa Time (UTC+3)
EAT = timezone(timedelta(hours=3))

def now_eat():
    return datetime.now(EAT)

# Root endpoint - serve main page
@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    with open("dashboard.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/loan-request", response_class=HTMLResponse)
async def loan_request():
    with open("loan_request.html", "r") as f:
        return HTMLResponse(content=f.read())

# Authentication endpoints
@app.post("/api/auth/register")
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == user_data.email) | (User.phone == user_data.phone)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or phone already exists"
        )
    
    if len(user_data.password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot be longer than 72 characters."
        )
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        phone=user_data.phone,
        password_hash=hashed_password
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create access token
    access_token = create_access_token(data={"sub": new_user.id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "phone": new_user.phone
        }
    }

@app.post("/api/auth/login")
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    if len(user_data.password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot be longer than 72 characters."
        )
    user = authenticate_user(db, user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token(data={"sub": user.id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "phone": user.phone
        }
    }

# User profile endpoints
@app.get("/api/users/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "phone": current_user.phone,
        "created_at": current_user.created_at,
        "payhero_account_id": current_user.payhero_account_id
    }

# Savings endpoints
@app.post("/api/savings/goals")
async def create_savings_goal(
    goal_data: SavingsGoalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    new_goal = SavingsGoal(
        user_id=current_user.id,
        goal_name=goal_data.goal_name,
        target_amount=goal_data.target_amount,
        target_date=goal_data.target_date
    )
    
    db.add(new_goal)
    db.commit()
    db.refresh(new_goal)
    
    return {
        "id": new_goal.id,
        "goal_name": new_goal.goal_name,
        "target_amount": new_goal.target_amount,
        "current_amount": new_goal.current_amount,
        "target_date": new_goal.target_date,
        "progress": (new_goal.current_amount / new_goal.target_amount) * 100
    }

@app.get("/api/savings/goals")
async def get_savings_goals(
    current_user: User = Depends(get_current_user),  # <-- This requires a valid token
    db: Session = Depends(get_db)
):
    goals = db.query(SavingsGoal).filter(
        SavingsGoal.user_id == current_user.id,
        SavingsGoal.is_active == True
    ).all()
      
    return [
        {
            "id": goal.id,
            "goal_name": goal.goal_name,
            "target_amount": goal.target_amount,
            "current_amount": goal.current_amount,
            "target_date": goal.target_date,
            "progress": (goal.current_amount / goal.target_amount) * 100 if goal.target_amount > 0 else 0
        }
        for goal in goals
    ]

@app.post("/api/savings/transactions")
async def add_savings_transaction(
    transaction_data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Create transaction
    new_transaction = Transaction(
        user_id=current_user.id,
        amount=transaction_data.amount,
        transaction_type=transaction_data.transaction_type,
        description=transaction_data.description
    )
    db.add(new_transaction)

    # Update specific savings goal if it's a savings transaction
    if transaction_data.transaction_type == "savings":
        if not transaction_data.goal_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="goal_id is required for savings transactions"
            )
        goal = db.query(SavingsGoal).filter(
            SavingsGoal.id == transaction_data.goal_id,
            SavingsGoal.user_id == current_user.id,
            SavingsGoal.is_active == True
        ).first()
        if not goal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Savings goal not found"
            )
        goal.current_amount += transaction_data.amount

    db.commit()
    db.refresh(new_transaction)

    return {
        "id": new_transaction.id,
        "amount": new_transaction.amount,
        "transaction_type": new_transaction.transaction_type,
        "description": new_transaction.description,
        "timestamp": new_transaction.timestamp
    }

@app.get("/api/savings/balance")
async def get_savings_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Sum current_amount of all active savings goals
    active_goals = db.query(SavingsGoal).filter(
        SavingsGoal.user_id == current_user.id,
        SavingsGoal.is_active == True
    ).all()
    total_savings = sum(goal.current_amount for goal in active_goals)

    # Calculate total loans
    loan_transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type == "loan"
    ).all()
    total_loans = sum(t.amount for t in loan_transactions)
    available_balance = total_savings - total_loans

    return {
        "total_savings": total_savings,
        "total_loans": total_loans,
        "available_balance": available_balance,
        "loan_eligible_amount": total_savings * 0.8  # 80% of all savings goals
    }

# AI Classification endpoints
@app.post("/api/ai/classify")
async def classify_transaction(request: ClassificationRequest):
    try:
        result = classifier.classify_transaction(request.description)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Classification failed: {str(e)}"
        )

# Loan endpoints
@app.post("/api/loans/request")
async def request_loan(
    loan_request: LoanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get user's savings balance
    balance_info = await get_savings_balance(current_user, db)
    available_for_loan = balance_info["loan_eligible_amount"]
    
    if loan_request.amount > available_for_loan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Loan amount exceeds available balance. Maximum: KES {available_for_loan:.2f}"
        )
    
    # Classify the loan reason
    classification = classifier.classify_transaction(loan_request.reason)
    
    # Create loan record
    due_date = now_eat() + timedelta(days=30)  # 30-day loan term
    new_loan = Loan(
        user_id=current_user.id,
        amount=loan_request.amount,
        reason=loan_request.reason,
        due_date=due_date,
        ai_category=classification["category"],
        ai_confidence=classification["confidence"],
        interest_rate=0.05  # <-- set default interest rate (10%)
    )
    
    db.add(new_loan)
    db.commit()
    db.refresh(new_loan)

    # Record the loan transaction so future loan eligibility is reduced
    loan_transaction = Transaction(
        user_id=current_user.id,
        amount=loan_request.amount,
        transaction_type="loan",
        description=f"Shielded loan: {loan_request.reason}",
        category=classification["category"]
    )
    db.add(loan_transaction)
    db.commit()
    db.refresh(loan_transaction)

    # Calculate repayment amount before creating schedule
    repayment_amount = loan_request.amount * (1 + new_loan.interest_rate)

    # Create repayment schedule (simplified: single payment)
    repayment_schedule = RepaymentSchedule(
        loan_id=new_loan.id,
        installment_amount=repayment_amount,
        due_date=due_date
    )
    db.add(repayment_schedule)
    db.commit()
    db.refresh(new_loan)

    return {
        "loan_id": new_loan.id,
        "amount": new_loan.amount,
        "interest_rate": new_loan.interest_rate,
        "due_date": new_loan.due_date,
        "total_repayment": repayment_amount,
        "ai_classification": {
            "category": classification["category"],
            "confidence": classification["confidence"],
            "is_emergency": classification["is_emergency"],
            "recommendation": classification["recommendation"]
        },
        "status": "approved"
    }

@app.get("/api/loans")
async def get_user_loans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    loans = db.query(Loan).filter(Loan.user_id == current_user.id).all()
    
    return [
        {
            "id": loan.id,
            "amount": loan.amount,
            "reason": loan.reason,
            "status": loan.status,
            "interest_rate": loan.interest_rate,
            "due_date": loan.due_date,
            "repaid_amount": loan.repaid_amount,
            "ai_category": loan.ai_category,
            "ai_confidence": loan.ai_confidence,
            "created_at": loan.created_at
        }
        for loan in loans
    ]

@app.get("/api/transactions")
async def get_user_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.timestamp.desc()).limit(50).all()
    
    return [
        {
            "id": transaction.id,
            "amount": transaction.amount,
            "transaction_type": transaction.transaction_type,
            "description": transaction.description,
            "category": transaction.category,
            "timestamp": transaction.timestamp
        }
        for transaction in transactions
    ]

# PayHero simulation endpoints
@app.post("/api/payhero/simulate-payment")
async def simulate_payhero_payment(
    amount: float,
    description: str,
    current_user: User = Depends(get_current_user)
):
    # Simulate PayHero payment response
    import random
    import string
    
    transaction_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    
    return {
        "transaction_id": transaction_id,
        "status": "success",
        "amount": amount,
        "description": description,
        "mpesa_receipt": f"OEI{transaction_id}",
        "timestamp": now_eat().isoformat()
    }

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": now_eat().isoformat()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)