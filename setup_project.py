import os

def create_file(path, content):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')

def main():
    print("Setting up SkillPulse AI Full-Stack Project...")

    # ==========================================
    # BACKEND
    # ==========================================
    create_file('backend/requirements.txt', """
fastapi==0.103.1
uvicorn==0.23.2
sqlalchemy==2.0.20
pydantic==2.3.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
scikit-learn==1.3.0
spacy==3.6.1
pandas==2.1.0
PyPDF2==3.0.1
""")

    create_file('backend/database.py', """
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Date, ForeignKey, Float
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./skillpulse.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    location = Column(String)
    date_posted = Column(Date)

class Skill(Base):
    __tablename__ = "skills"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)

class JobSkill(Base):
    __tablename__ = "job_skills"
    job_id = Column(Integer, ForeignKey("jobs.id"), primary_key=True)
    skill_id = Column(Integer, ForeignKey("skills.id"), primary_key=True)

class Forecast(Base):
    __tablename__ = "forecasts"
    id = Column(Integer, primary_key=True, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id"))
    month = Column(Date)
    projected_demand = Column(Float)

Base.metadata.create_all(bind=engine)
""")

    create_file('backend/auth.py', """
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import SessionLocal, User

SECRET_KEY = "your-very-secret-key-change-in-prod"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user
""")

    create_file('backend/ml_engine.py', """
import spacy
from dateutil import parser
import string
from collections import defaultdict
import datetime
from sklearn.linear_model import LinearRegression
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from database import Job, Skill, JobSkill, Forecast

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("SpaCy model 'en_core_web_sm' not found. It will be downloaded automatically by the setup script.")
    nlp = None

PREDEFINED_SKILLS = {
    "python", "java", "sql", "aws", "react", "machine learning", "deep learning",
    "nlp", "kubernetes", "docker", "javascript", "typescript", "c++", "c#",
    "golang", "rust", "azure", "gcp", "agile", "scrum", "tensorflow", "pytorch",
    "pandas", "scikit-learn", "data analysis", "tableau", "power bi", "hadoop", "spark"
}

def extract_skills_from_text(text: str):
    text = text.lower()
    extracted = set()
    # Simple dictionary matching approach combined with basic tokenization
    # Since SpaCy tokenizer handles punctuation better
    if nlp is not None:
        doc = nlp(text)
        tokens = [token.text for token in doc]
        text = " " + " ".join(tokens) + " "
    else:
        text = " " + text.translate(str.maketrans('', '', string.punctuation)) + " "
        
    for skill in PREDEFINED_SKILLS:
        if f" {skill} " in text:
            extracted.add(skill)
    return list(extracted)

def train_forecasts(db: Session):
    jobs = db.query(Job).all()
    job_skills = db.query(JobSkill).all()
    skills = {s.id: s.name for s in db.query(Skill).all()}
    
    if not jobs or not job_skills:
        return
        
    df_jobs = pd.DataFrame([{"job_id": j.id, "month": j.date_posted.replace(day=1)} for j in jobs])
    df_js = pd.DataFrame([{"job_id": js.job_id, "skill_id": js.skill_id} for js in job_skills])
    
    df = pd.merge(df_js, df_jobs, on="job_id")
    monthly_counts = df.groupby(['skill_id', 'month']).size().reset_index(name='count')
    
    # Store next 12 months forecast
    db.query(Forecast).delete()
    
    for skill_id in monthly_counts['skill_id'].unique():
        skill_data = monthly_counts[monthly_counts['skill_id'] == skill_id].sort_values('month')
        if len(skill_data) < 2:
            continue
            
        months_numeric = np.arange(len(skill_data)).reshape(-1, 1)
        counts = skill_data['count'].values
        
        model = LinearRegression()
        model.fit(months_numeric, counts)
        
        last_month = skill_data['month'].iloc[-1]
        
        for i in range(1, 13):
            pred_month = last_month + pd.DateOffset(months=i)
            # using month numeric for simple projection
            pred_demand = model.predict([[len(skill_data) - 1 + i]])[0]
            pred_demand = max(0, pred_demand) # non-negative
            
            f = Forecast(skill_id=skill_id, month=pred_month.date(), projected_demand=pred_demand)
            db.add(f)
            
    db.commit()
""")

    create_file('backend/main.py', """
from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
import pandas as pd
import io
import datetime
from dateutil import parser

from database import engine, SessionLocal, User, Job, Skill, JobSkill, Forecast
from auth import get_db, get_password_hash, verify_password, create_access_token, get_current_user
from ml_engine import extract_skills_from_text, train_forecasts

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
    
    hashed_password = get_password_hash(user.password)
    new_user = User(email=user.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token(data={"sub": new_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/jobs/upload")
async def upload_jobs(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
    content = await file.read()
    df = pd.read_csv(io.BytesIO(content))
    
    desc_col = next((col for col in df.columns if 'desc' in col.lower() or 'text' in col.lower()), None)
    title_col = next((col for col in df.columns if 'title' in col.lower() or 'role' in col.lower()), None)
    
    if not desc_col:
        raise HTTPException(status_code=400, detail="Cannot find description column in CSV")
        
    jobs_added = 0
    skills_added = set()
    
    for _, row in df.iterrows():
        desc = str(row[desc_col]) if pd.notnull(row[desc_col]) else ""
        title = str(row[title_col]) if title_col and pd.notnull(row[title_col]) else "Unknown Title"
        
        # Simple date handling
        date_posted = datetime.date.today()
        for c in df.columns:
            if 'date' in c.lower() and pd.notnull(row[c]):
                try:
                    date_posted = parser.parse(str(row[c])).date()
                    break
                except:
                    pass
        
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
            skills_added.add(s)
            
        jobs_added += 1
        
    db.commit()
    
    # Trigger re-training of forecast model
    train_forecasts(db)
    
    return {"message": f"Successfully processed {jobs_added} jobs. Extracted {len(skills_added)} unique skills."}

@app.get("/api/analytics/trends")
def get_trends(db: Session = Depends(get_db)):
    # Get top skills for current month
    query = (
        db.query(Skill.name, func.count(JobSkill.job_id).label("count"))
        .join(JobSkill, Skill.id == JobSkill.skill_id)
        .group_by(Skill.name)
        .order_by(func.count(JobSkill.job_id).desc())
        .limit(10)
    )
    
    results = query.all()
    # Format for chart: array of {name, count}
    data = [{"skill": r.name, "count": r.count} for r in results]
    return data

@app.get("/api/analytics/forecast")
def get_forecast(db: Session = Depends(get_db)):
    forecasts = db.query(Forecast).all()
    skills = {s.id: s.name for s in db.query(Skill).all()}
    
    formatted = {}
    for f in forecasts:
        s_name = skills[f.skill_id]
        if s_name not in formatted:
            formatted[s_name] = []
        formatted[s_name].append({
            "month": f.month.isoformat(),
            "projected": float(f.projected_demand)
        })
        
    return formatted

@app.post("/api/resume/analyze")
async def analyze_resume(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    text = ""
    if file.filename.endswith(".pdf"):
        import PyPDF2
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(await file.read()))
        for page in pdf_reader.pages:
            text += page.extract_text() + " "
    else:
        content = await file.read()
        text = content.decode('utf-8', errors='ignore')
        
    user_skills = extract_skills_from_text(text)
    
    # Compare with top 5 highest demanded skills in DB (historical + forecasted logic roughly)
    top_skills = [r.name for r in db.query(Skill.name, func.count(JobSkill.job_id).label("count"))
                                .join(JobSkill, Skill.id == JobSkill.skill_id)
                                .group_by(Skill.name)
                                .order_by(func.count(JobSkill.job_id).desc())
                                .limit(5).all()]
                                
    if not top_skills:
        top_skills = ["python", "sql", "aws", "react", "machine learning"]
        
    matched = [s for s in top_skills if s in user_skills]
    missing = [s for s in top_skills if s not in user_skills]
    
    score = int((len(matched) / len(top_skills)) * 100) if top_skills else 0
    
    return {
        "score": score,
        "matched": matched,
        "missing": missing,
        "extracted_skills": user_skills,
        "target_top_skills": top_skills
    }
""")

    # ==========================================
    # FRONTEND
    # ==========================================
    create_file('frontend/package.json', """{
  "name": "skillpulse-frontend",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.10.0",
    "recharts": "^2.12.0"
  },
  "devDependencies": {
    "@types/react": "^18.0.28",
    "@types/react-dom": "^18.0.11",
    "@vitejs/plugin-react": "^3.1.0",
    "vite": "^4.2.0"
  }
}
""")

    create_file('frontend/vite.config.js', """
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})
""")

    create_file('frontend/index.html', """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>SkillPulse AI</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;800&display=swap" rel="stylesheet">
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
""")

    create_file('frontend/src/index.css', """
:root {
  --bg-primary: #0f172a;
  --bg-secondary: #1e1b4b;
  --text-primary: #f8fafc;
  --text-secondary: #cbd5e1;
  --accent-primary: #6366f1;
  --accent-secondary: #8b5cf6;
  --success: #10b981;
  --danger: #ef4444;
  --glass-bg: rgba(255, 255, 255, 0.03);
  --glass-border: rgba(255, 255, 255, 0.08);
}
* { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
body { background: linear-gradient(135deg, var(--bg-primary), var(--bg-secondary)); color: var(--text-primary); min-height: 100vh; }
h1, h2, h3 { font-family: 'Outfit', sans-serif; }

/* Blob Accents */
.blob { position: fixed; border-radius: 50%; filter: blur(100px); z-index: -1; opacity: 0.3; }
.blob-1 { top: -100px; left: -100px; width: 400px; height: 400px; background: var(--accent-primary); }
.blob-2 { bottom: -100px; right: -100px; width: 400px; height: 400px; background: var(--accent-secondary); }

/* Layout */
.app-container { display: flex; height: 100vh; width: 100vw; overflow: hidden;}
.sidebar { width: 260px; background: var(--glass-bg); border-right: 1px solid var(--glass-border); padding: 2rem; display: flex; flex-direction: column; gap: 1rem; }
.main-content { flex: 1; padding: 2rem; overflow-y: auto; }

.brand { font-size: 1.5rem; font-weight: 800; background: linear-gradient(to right, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 2rem; }
.nav-link { padding: 0.75rem 1rem; border-radius: 0.75rem; color: var(--text-secondary); text-decoration: none; font-weight: 500; transition: 0.3s; }
.nav-link:hover, .nav-link.active { background: rgba(255,255,255,0.1); color: white; }

/* Components */
.card { background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 1rem; padding: 1.5rem; backdrop-filter: blur(10px); }
.grid { display: grid; gap: 1.5rem; }
.grid-2 { grid-template-columns: 1fr 1fr; }
.grid-3 { grid-template-columns: 1fr 1fr 1fr; }

.form-group { margin-bottom: 1rem; }
.form-group label { display: block; margin-bottom: 0.5rem; color: var(--text-secondary); font-size: 0.875rem; }
.form-input { width: 100%; padding: 0.75rem; background: rgba(0,0,0,0.2); border: 1px solid var(--glass-border); border-radius: 0.5rem; color: white; outline: none; }
.form-input:focus { border-color: var(--accent-primary); }

.btn { padding: 0.75rem 1.5rem; border: none; border-radius: 0.5rem; cursor: pointer; font-weight: 600; color: white; transition: 0.3s; }
.btn-primary { background: linear-gradient(45deg, var(--accent-primary), var(--accent-secondary)); }
.btn-primary:hover { opacity: 0.9; transform: translateY(-2px); }
.btn-outline { background: transparent; border: 1px solid var(--glass-border); }
.btn-outline:hover { background: rgba(255,255,255,0.1); }

/* Login center */
.auth-container { display: flex; justify-content: center; align-items: center; height: 100vh; }
.auth-card { width: 100%; max-width: 400px; }

.badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 1rem; font-size: 0.875rem; }
.badge-success { background: rgba(16, 185, 129, 0.2); color: #34d399; }
.badge-danger { background: rgba(239, 68, 68, 0.2); color: #f87171; }
""")

    create_file('frontend/src/main.jsx', """
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'
import { BrowserRouter } from 'react-router-dom'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
""")

    create_file('frontend/src/App.jsx', """
import { Routes, Route, useNavigate, useLocation, Link } from 'react-router-dom';
import { useState, useEffect } from 'react';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import UploadJob from './pages/UploadJob';
import ResumeAnalyzer from './pages/ResumeAnalyzer';

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (token) localStorage.setItem('token', token);
    else localStorage.removeItem('token');
  }, [token]);

  const logout = () => {
    setToken(null);
    navigate('/login');
  };

  if (!token && location.pathname !== '/register') {
    return <Login setToken={setToken} />;
  }

  if (!token && location.pathname === '/register') {
    return <Register setToken={setToken} />;
  }

  return (
    <div className="app-container">
      <div className="blob blob-1"></div>
      <div className="blob blob-2"></div>
      
      <div className="sidebar">
        <div className="brand">⚡ SkillPulse AI</div>
        <Link className="nav-link" to="/">📊 Dashboard & Trends</Link>
        <Link className="nav-link" to="/upload-job">📥 Upload Job Feed</Link>
        <Link className="nav-link" to="/resume">🧑‍💻 Resume Analyzer</Link>
        <div style={{flex: 1}}></div>
        <button onClick={logout} className="btn btn-outline">Logout</button>
      </div>

      <div className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/upload-job" element={<UploadJob />} />
          <Route path="/resume" element={<ResumeAnalyzer />} />
        </Routes>
      </div>
    </div>
  );
}
""")

    create_file('frontend/src/pages/Login.jsx', """
import { useState } from 'react';
import { Link } from 'react-router-dom';

export default function Login({ setToken }) {
  const [email, setEmail] = useState('demo@example.com');
  const [password, setPassword] = useState('demo123');
  const [error, setError] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    const formData = new URLSearchParams();
    formData.append('username', email); // OAuth2 expects username
    formData.append('password', password);

    try {
      const res = await fetch('http://localhost:8000/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        setToken(data.access_token);
      } else {
        setError(data.detail);
      }
    } catch (err) {
      setError("Cannot connect to server.");
    }
  };

  return (
    <div className="auth-container">
      <div className="blob blob-1"></div>
      <div className="card auth-card">
        <h2 style={{textAlign:'center', marginBottom: '1.5rem'}}>Login to SkillPulse</h2>
        {error && <div style={{color:'red', marginBottom:'1rem'}}>{error}</div>}
        <form onSubmit={handleLogin}>
          <div className="form-group">
            <label>Email</label>
            <input className="form-input" type="email" value={email} onChange={e=>setEmail(e.target.value)} required />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input className="form-input" type="password" value={password} onChange={e=>setPassword(e.target.value)} required />
          </div>
          <button className="btn btn-primary" style={{width: '100%', marginBottom:'1rem'}}>Login</button>
        </form>
        <p style={{textAlign:'center', fontSize: '0.875rem', color:'var(--text-secondary)'}}>
          Need an account? <Link to="/register" style={{color: 'var(--accent-primary)'}}>Sign up</Link>
        </p>
      </div>
    </div>
  );
}
""")

    create_file('frontend/src/pages/Register.jsx', """
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

export default function Register({ setToken }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('http://localhost:8000/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();
      if (res.ok) {
        setToken(data.access_token);
        navigate('/');
      } else {
        setError(data.detail);
      }
    } catch (err) {
      setError("Cannot connect to server.");
    }
  };

  return (
    <div className="auth-container">
      <div className="blob blob-1"></div>
      <div className="card auth-card">
        <h2 style={{textAlign:'center', marginBottom: '1.5rem'}}>Create Account</h2>
        {error && <div style={{color:'red', marginBottom:'1rem'}}>{error}</div>}
        <form onSubmit={handleRegister}>
          <div className="form-group">
            <label>Email</label>
            <input className="form-input" type="email" value={email} onChange={e=>setEmail(e.target.value)} required />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input className="form-input" type="password" value={password} onChange={e=>setPassword(e.target.value)} required />
          </div>
          <button className="btn btn-primary" style={{width: '100%', marginBottom:'1rem'}}>Sign Up</button>
        </form>
        <p style={{textAlign:'center', fontSize: '0.875rem', color:'var(--text-secondary)'}}>
          Already have an account? <Link to="/login" style={{color: 'var(--accent-primary)'}}>Login</Link>
        </p>
      </div>
    </div>
  );
}
""")

    create_file('frontend/src/pages/Dashboard.jsx', """
import { useState, useEffect } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

export default function Dashboard() {
  const [trends, setTrends] = useState([]);
  const [forecast, setForecast] = useState({});

  useEffect(() => {
    fetch('http://localhost:8000/api/analytics/trends')
      .then(res => res.json())
      .then(data => setTrends(data));
      
    fetch('http://localhost:8000/api/analytics/forecast')
      .then(res => res.json())
      .then(data => setForecast(data));
  }, []);

  const forecastSkills = Object.keys(forecast);

  return (
    <div>
      <h1 style={{marginBottom: '2rem'}}>📈 Demand Analytics Dashboard</h1>
      
      <div className="grid grid-2" style={{marginBottom: '2rem'}}>
        <div className="card">
          <h2>Current Top Skills (Aggregated)</h2>
          <div style={{height: 300, marginTop: '1rem'}}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={trends} layout="vertical" margin={{ left: 40 }}>
                <XAxis type="number" hide />
                <YAxis dataKey="skill" type="category" stroke="#cbd5e1" />
                <Tooltip cursor={{fill: 'rgba(255,255,255,0.05)'}} contentStyle={{backgroundColor: '#1e1b4b', border: 'none', borderRadius: '8px'}} />
                <Bar dataKey="count" fill="url(#colorGradient)" radius={[0, 4, 4, 0]} />
                <defs>
                  <linearGradient id="colorGradient" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#6366f1" />
                    <stop offset="100%" stopColor="#ec4899" />
                  </linearGradient>
                </defs>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <h2>12-Month Predictive Forecast Engine</h2>
          {forecastSkills.length > 0 ? (
            <div style={{height: 300, marginTop: '1rem'}}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={forecast[forecastSkills[0]]}>
                  <XAxis dataKey="month" stroke="#cbd5e1" tickFormatter={(v)=>v.substring(0,7)} />
                  <YAxis stroke="#cbd5e1" />
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
                  <Tooltip contentStyle={{backgroundColor: '#1e1b4b', border: 'none', borderRadius: '8px'}} />
                  <Line type="monotone" dataKey="projected" stroke="#f59e0b" strokeWidth={3} dot={false} />
                </LineChart>
              </ResponsiveContainer>
              <p style={{textAlign: 'center', color: 'var(--text-secondary)', marginTop: '1rem'}}>
                Showing forecast for <strong>{forecastSkills[0]}</strong>
              </p>
            </div>
          ) : (
            <p style={{marginTop: '1rem', color: 'var(--text-secondary)'}}>Upload Job Data to generate forecasts.</p>
          )}
        </div>
      </div>
    </div>
  );
}
""")

    create_file('frontend/src/pages/UploadJob.jsx', """
import { useState } from 'react';

export default function UploadJob() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(false);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    
    setLoading(true);
    setStatus('Uploading and invoking NLP pipeline...');
    
    const formData = new FormData();
    formData.append('file', file);

    const token = localStorage.getItem('token');

    try {
      const res = await fetch('http://localhost:8000/api/jobs/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        setStatus(`✅ Success: ${data.message}`);
      } else {
        setStatus(`❌ Error: ${data.detail}`);
      }
    } catch (err) {
      setStatus("Error uploading file.");
    }
    setLoading(false);
  };

  return (
    <div className="card" style={{maxWidth: '600px', margin: '0 auto'}}>
      <h2>📥 Ingest Job Descriptions (CSV)</h2>
      <p style={{color: 'var(--text-secondary)', marginBottom: '1.5rem', marginTop: '0.5rem'}}>
        Upload a CSV dataset containing job postings. The NLP engine (SpaCy) will extract technical skills and update the trend databases.
      </p>

      <form onSubmit={handleUpload}>
        <div className="form-group">
          <label>Select CSV File</label>
          <input type="file" className="form-input" accept=".csv" onChange={e => setFile(e.target.files[0])} />
        </div>
        <button className="btn btn-primary" disabled={loading} style={{width: '100%'}}>
          {loading ? 'Processing...' : 'Ingest Data'}
        </button>
      </form>
      
      {status && (
        <div style={{marginTop: '1.5rem', padding: '1rem', background: 'rgba(255,255,255,0.05)', borderRadius: '8px'}}>
          {status}
        </div>
      )}
    </div>
  );
}
""")

    create_file('frontend/src/pages/ResumeAnalyzer.jsx', """
import { useState } from 'react';

export default function ResumeAnalyzer() {
  const [file, setFile] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    
    setLoading(true);
    
    const formData = new FormData();
    formData.append('file', file);

    const token = localStorage.getItem('token');

    try {
      const res = await fetch('http://localhost:8000/api/resume/analyze', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });
      const data = await res.json();
      if (res.ok) setResults(data);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  return (
    <div>
      <h1 style={{marginBottom: '2rem'}}>🧑‍💻 Resume Skill Gap Analyzer</h1>
      
      <div className="grid grid-2">
        <div className="card">
          <h2>Upload Resume</h2>
          <p style={{color: 'var(--text-secondary)', marginBottom: '1.5rem'}}>
            Extracts your skills using NLP and compares them against current topmost demanded tech skills. (.PDF or .TXT)
          </p>

          <form onSubmit={handleUpload}>
            <div className="form-group">
              <input type="file" className="form-input" accept=".pdf,.txt" onChange={e => setFile(e.target.files[0])} />
            </div>
            <button className="btn btn-primary" disabled={loading}>
              {loading ? 'Analyzing...' : 'Analyze My Profile'}
            </button>
          </form>
        </div>

        {results && (
          <div className="card">
            <h2>Analysis Results</h2>
            <div style={{marginTop: '1.5rem', display: 'flex', alignItems: 'center', gap: '1rem'}}>
              <div style={{fontSize: '3rem', fontWeight: 'bold', color: results.score > 50 ? 'var(--success)' : 'var(--danger)'}}>
                {results.score}%
              </div>
              <div style={{color: 'var(--text-secondary)'}}>Readiness against Top Market Skills</div>
            </div>

            <div style={{marginTop: '1.5rem'}}>
              <h4>✅ Matched Market Skills</h4>
              <div style={{display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.5rem'}}>
                {results.matched.map(s => <span key={s} className="badge badge-success">{s}</span>)}
                {results.matched.length === 0 && <span style={{color: 'var(--text-secondary)'}}>None</span>}
              </div>
            </div>

            <div style={{marginTop: '1.5rem'}}>
              <h4>❌ Missing Market Skills (Gap)</h4>
              <div style={{display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.5rem'}}>
                {results.missing.map(s => <span key={s} className="badge badge-danger">{s}</span>)}
                {results.missing.length === 0 && <span style={{color: 'var(--text-secondary)'}}>None</span>}
              </div>
            </div>
            
            <div style={{marginTop: '1.5rem', fontSize: '0.875rem', color: 'var(--text-secondary)'}}>
              <strong>Your Extracted Skills: </strong> {results.extracted_skills.join(', ')}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
""")

    create_file('setup_instructions.md', """
# SkillPulse AI Platform 🚀

This is a full-stack iteration of SkillPulse AI with a Python FastAPI backend and a React Vite frontend.

## 1. Backend Setup (FastAPI)

1. Navigate to the `backend` folder:
   ```bash
   cd backend
   ```
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   pip install -r requirements.txt
   ```
3. Download the SpaCy NLP ML model:
   ```bash
   python -m spacy download en_core_web_sm
   ```
4. Start the backend server:
   ```bash
   uvicorn main:app --reload
   ```
   *The API will be available at http://localhost:8000*

## 2. Frontend Setup (React/Vite)

1. Start a new terminal and navigate to the `frontend` folder:
   ```bash
   cd frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
   *The React app will likely run on http://localhost:5173*
""")

if __name__ == "__main__":
    main()
