from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
import pandas as pd
import io
import datetime
from dateutil import parser

from database import engine, SessionLocal, User, Job, Skill, JobSkill, Forecast
from auth import get_db, get_password_hash, verify_password, create_access_token, get_current_user
from ml_engine import extract_skills_from_text, train_forecasts, ROLE_ARCHETYPES

app = FastAPI(title="SkillPulse AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserCreate(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

@app.post("/api/auth/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(email=user.email, hashed_password=get_password_hash(user.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"access_token": create_access_token(data={"sub": new_user.email}), "token_type": "bearer"}

@app.post("/api/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    return {"access_token": create_access_token(data={"sub": user.email}), "token_type": "bearer"}

@app.post("/api/jobs/upload")
async def upload_jobs(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
    content = await file.read()
    df = pd.read_csv(io.BytesIO(content))
    
    desc_col = next((c for c in df.columns if 'desc' in c.lower() or 'text' in c.lower()), None)
    title_col = next((c for c in df.columns if 'title' in c.lower() or 'role' in c.lower()), None)
    
    if not desc_col:
        raise HTTPException(status_code=400, detail="Cannot find description column")
        
    jobs_added = 0
    
    for _, row in df.iterrows():
        desc = str(row[desc_col]) if pd.notnull(row[desc_col]) else ""
        title = str(row[title_col]) if title_col and pd.notnull(row[title_col]) else "Unknown"
        
        date_posted = datetime.date.today()
        for c in df.columns:
            if 'date' in c.lower() and pd.notnull(row[c]):
                try:
                    date_posted = parser.parse(str(row[c])).date()
                    break
                except: pass
        
        new_job = Job(title=title, description=desc, location="Remote", date_posted=date_posted)
        db.add(new_job)
        db.flush()
        
        skills = extract_skills_from_text(desc)
        for s in skills:
            skill_db = db.query(Skill).filter(Skill.name == s).first()
            if not skill_db:
                skill_db = Skill(name=s)
                db.add(skill_db)
                db.flush()
            db.add(JobSkill(job_id=new_job.id, skill_id=skill_db.id))
        jobs_added += 1
        
    db.commit()
    train_forecasts(db)
    
    return {"message": f"Ingested {jobs_added} jobs."}


@app.get("/api/analytics/trends")
def get_trends(db: Session = Depends(get_db)):
    query = (
        db.query(Skill.name, func.count(JobSkill.job_id).label("count"))
        .join(JobSkill, Skill.id == JobSkill.skill_id)
        .group_by(Skill.name)
        .order_by(func.count(JobSkill.job_id).desc())
        .limit(10)
    )
    return [{"skill": r.name, "count": r.count} for r in query.all()]


@app.get("/api/analytics/forecast")
def get_forecast(db: Session = Depends(get_db)):
    forecasts = db.query(Forecast).all()
    skills = {s.id: s.name for s in db.query(Skill).all()}
    
    res = {}
    for f in forecasts:
        s_name = skills[f.skill_id]
        if s_name not in res:
            res[s_name] = []
        res[s_name].append({"month": f.month.isoformat(), "projected": float(f.projected_demand)})
    return res

@app.post("/api/resume/analyze")
async def analyze_resume(
    file: UploadFile = File(...), 
    custom_role: str = Form(None), 
    custom_skills: str = Form(None), 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    text = ""
    if file.filename.endswith(".pdf"):
        import PyPDF2
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(await file.read()))
        for page in pdf_reader.pages: text += page.extract_text() + " "
    else:
        text = (await file.read()).decode('utf-8', errors='ignore')
        
    user_skills = extract_skills_from_text(text)
    
    target_skills = []
    if custom_role and custom_role.lower() in ROLE_ARCHETYPES:
        target_skills = list(ROLE_ARCHETYPES[custom_role.lower()])
    elif custom_skills:
        target_skills = [s.strip().lower() for s in custom_skills.split(',') if s.strip()]
    else:
        # Default fallback to top db skills
        top = db.query(Skill.name).join(JobSkill).group_by(Skill.name).order_by(func.count(JobSkill.job_id).desc()).limit(7).all()
        target_skills = [r.name for r in top] if top else ["python", "sql", "aws", "react", "machine learning"]

    matched = [s for s in target_skills if s in user_skills]
    missing = [s for s in target_skills if s not in user_skills]
    
    score = int((len(matched) / len(target_skills)) * 100) if target_skills else 0
    
    return {
        "score": score,
        "matched": matched,
        "missing": missing,
        "extracted_skills": user_skills,
        "role_assessed": custom_role or "General Market Top Skills"
    }
