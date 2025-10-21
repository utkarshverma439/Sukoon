from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import json

from database import get_db, create_tables, User, Chat, Summary
from llm_client import chat_with_bot, summarize_conversation

app = FastAPI(title="Sukoon - Mental Wellness App")

# Security
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Create database tables
create_tables()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None
    
    user = db.query(User).filter(User.username == username).first()
    return user

@app.get("/", response_class=HTMLResponse)
async def root(request: Request, current_user: User = Depends(get_current_user)):
    if current_user:
        return RedirectResponse(url="/chat", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
async def signup(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    age: int = Form(...),
    gender: str = Form(...),
    db: Session = Depends(get_db)
):
    # Validate age
    if age < 1 or age > 120:
        return templates.TemplateResponse("signup.html", {
            "request": request, 
            "error": "Please enter a valid age between 1 and 120"
        })
    
    # Check if user exists (by email)
    if db.query(User).filter(User.email == email).first():
        return templates.TemplateResponse("signup.html", {
            "request": request, 
            "error": "Email already exists"
        })
    
    # Create user
    hashed_password = get_password_hash(password)
    user = User(
        username=email,  # Use email as username for login
        email=email,
        full_name=full_name,
        age=age,
        gender=gender,
        password_hash=hashed_password
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create access token and redirect to assessment
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/assessment", status_code=302)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),  # This will actually be email from the form
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Look up user by email (which comes in as 'username' from the form)
    user = db.query(User).filter(User.email == username).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid email or password"
        })
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/chat", status_code=302)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="access_token")
    return response

@app.get("/assessment", response_class=HTMLResponse)
async def assessment_page(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    # If already completed assessment, redirect to chat
    if current_user.assessment_data:
        return RedirectResponse(url="/chat", status_code=302)
    
    return templates.TemplateResponse("assessment.html", {"request": request})

@app.post("/assessment")
async def submit_assessment(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    form_data = await request.form()
    assessment_data = {
        "mood": form_data.get("mood"),
        "anxiety": form_data.get("anxiety"),
        "sleep": form_data.get("sleep"),
        "interest": form_data.get("interest"),
        "support": form_data.get("support"),
        "self_harm": form_data.get("self_harm"),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Check for crisis indicators
    crisis_detected = assessment_data.get("self_harm") in ["several_days", "more_than_half", "nearly_every_day"]
    
    # Save assessment
    current_user.assessment_data = assessment_data
    db.commit()
    
    if crisis_detected:
        return templates.TemplateResponse("crisis.html", {"request": request})
    
    return RedirectResponse(url="/chat", status_code=302)

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("chat.html", {"request": request, "user": current_user})

@app.post("/chat/{bot}")
async def chat_with_bot_endpoint(
    bot: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if bot not in ["aarav", "meera"]:
        raise HTTPException(status_code=400, detail="Invalid bot")
    
    data = await request.json()
    message = data.get("message", "").strip()
    via_call = data.get("via_call", False)
    
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    try:
        # Get recent conversation history
        recent_chats = db.query(Chat).filter(
            Chat.user_id == current_user.id,
            Chat.bot == bot
        ).order_by(Chat.timestamp.desc()).limit(6).all()
        recent_chats.reverse()  # Oldest first
        
        # Get user summaries for personalization
        user_summaries = db.query(Summary).filter(
            Summary.user_id == current_user.id,
            Summary.bot == bot
        ).order_by(Summary.created_at.desc()).limit(3).all()
        
        # Get bot response with personalization
        reply = await chat_with_bot(bot, message, recent_chats, user_summaries)
        
        # Save conversation
        chat_record = Chat(
            user_id=current_user.id,
            bot=bot,
            message=message,
            reply=reply,
            via_call=via_call
        )
        db.add(chat_record)
        db.commit()
        
        # Auto-generate summary after every 8 messages for personalization
        total_messages = db.query(Chat).filter(
            Chat.user_id == current_user.id,
            Chat.bot == bot
        ).count()
        
        if total_messages % 8 == 0 and total_messages > 0:
            try:
                # Get recent conversation for summary
                summary_chats = db.query(Chat).filter(
                    Chat.user_id == current_user.id,
                    Chat.bot == bot
                ).order_by(Chat.timestamp.desc()).limit(8).all()
                summary_chats.reverse()
                
                # Generate summary for personalization
                summary_text = await summarize_conversation(bot, summary_chats)
                
                # Save summary
                summary = Summary(
                    user_id=current_user.id,
                    bot=bot,
                    summary_text=summary_text
                )
                db.add(summary)
                db.commit()
                
            except Exception as summary_error:
                # Don't fail the chat if summary fails
                print(f"Auto-summary failed: {summary_error}")
        
        return JSONResponse({"reply": reply})
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chats/{bot}")
async def get_chats(
    bot: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if bot not in ["aarav", "meera"]:
        raise HTTPException(status_code=400, detail="Invalid bot")
    
    chats = db.query(Chat).filter(
        Chat.user_id == current_user.id,
        Chat.bot == bot
    ).order_by(Chat.timestamp.asc()).all()
    
    return JSONResponse([{
        "message": chat.message,
        "reply": chat.reply,
        "timestamp": chat.timestamp.isoformat(),
        "via_call": chat.via_call
    } for chat in chats])

@app.post("/api/delete_chats/{bot}")
async def delete_chats(
    bot: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if bot not in ["aarav", "meera"]:
        raise HTTPException(status_code=400, detail="Invalid bot")
    
    # Delete chats and summaries
    db.query(Chat).filter(Chat.user_id == current_user.id, Chat.bot == bot).delete()
    db.query(Summary).filter(Summary.user_id == current_user.id, Summary.bot == bot).delete()
    db.commit()
    
    return JSONResponse({"message": f"Deleted all {bot} conversations"})

@app.post("/api/clear_all")
async def clear_all_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Delete all user data
    db.query(Chat).filter(Chat.user_id == current_user.id).delete()
    db.query(Summary).filter(Summary.user_id == current_user.id).delete()
    db.commit()
    
    return JSONResponse({"message": "Deleted all conversation data"})

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
