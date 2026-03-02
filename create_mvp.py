import os

def create_file(path, content):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')

def generate_backend():
    create_file("backend/requirements.txt", """
fastapi==0.103.1
uvicorn==0.23.2
sqlalchemy==2.0.24
pydantic==2.5.3
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
scikit-learn==1.3.0
spacy==3.7.2
pandas==2.1.0
PyPDF2==3.0.1
""")

    create_file("backend/database.py", """
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

    create_file("backend/auth.py", """
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import SessionLocal, User

SECRET_KEY = "mvp-secret-key-change-in-prod"
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

    create_file("backend/ml_engine.py", """
import spacy
from dateutil import parser
import string
import datetime
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sqlalchemy.orm import Session
from database import Job, Skill, JobSkill, Forecast

try:
    nlp = spacy.load("en_core_web_sm")
except BaseException:
    nlp = None

PREDEFINED_SKILLS = {
    "python", "java", "sql", "aws", "react", "machine learning", "deep learning",
    "nlp", "kubernetes", "docker", "javascript", "typescript", "c++", "c#",
    "golang", "rust", "azure", "gcp", "agile", "scrum", "tensorflow", "pytorch",
    "pandas", "scikit-learn", "data analysis", "tableau", "power bi", "hadoop", "spark",
    "node.js", "django", "flask", "fastapi"
}

ROLE_ARCHETYPES = {
    "data scientist": {"python", "sql", "machine learning", "pandas", "scikit-learn"},
    "software engineer": {"java", "python", "javascript", "react", "sql"},
    "cloud architect": {"aws", "azure", "kubernetes", "docker", "terraform"},
    "product manager": {"agile", "scrum", "data analysis", "tableau"}
}

def extract_skills_from_text(text: str):
    text = text.lower()
    extracted = set()

    if nlp is not None:
        doc = nlp(text)
        tokens = [token.text for token in doc]
        text_prepared = " " + " ".join(tokens) + " "
    else:
        text_prepared = " " + text.translate(str.maketrans('', '', string.punctuation)) + " "
        
    for skill in PREDEFINED_SKILLS:
        if f" {skill} " in text_prepared:
            extracted.add(skill)
    return list(extracted)

def train_forecasts(db: Session):
    jobs = db.query(Job).all()
    job_skills = db.query(JobSkill).all()
    
    if not jobs or not job_skills:
        return
        
    df_jobs = pd.DataFrame([{"job_id": j.id, "month": j.date_posted.replace(day=1)} for j in jobs])
    df_js = pd.DataFrame([{"job_id": js.job_id, "skill_id": js.skill_id} for js in job_skills])
    
    df = pd.merge(df_js, df_jobs, on="job_id")
    monthly_counts = df.groupby(['skill_id', 'month']).size().reset_index(name='count')
    
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
            try:
                pred_month = last_month + pd.DateOffset(months=i)
            except:
                continue
            pred_demand = model.predict([[len(skill_data) - 1 + i]])[0]
            pred_demand = max(0, pred_demand)
            
            f = Forecast(skill_id=skill_id, month=pred_month.date(), projected_demand=pred_demand)
            db.add(f)
            
    db.commit()
""")

    create_file("backend/main.py", """
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
""")

def generate_frontend():
    create_file("frontend/package.json", """{
  "name": "skillpulse-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": { "dev": "vite", "build": "vite build" },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.10.0",
    "recharts": "^2.12.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^3.1.0",
    "vite": "^4.2.0"
  }
}
""")
    create_file("frontend/vite.config.js", "import { defineConfig } from 'vite'; import react from '@vitejs/plugin-react'; export default defineConfig({ plugins: [react()] });")
    create_file("frontend/index.html", '<html lang="en"><head><title>SkillPulse AI</title><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Outfit:wght@600;800&display=swap" rel="stylesheet"></head><body><div id="root"></div><script type="module" src="/src/main.jsx"></script></body></html>')
    create_file("frontend/src/index.css", """
:root { --bg-primary: #0f172a; --bg-secondary: #1e1b4b; --text-primary: #f8fafc; --text-secondary: #cbd5e1; --accent-primary: #6366f1; --success: #10b981; --danger: #ef4444; }
* { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
body { background: linear-gradient(135deg, var(--bg-primary), var(--bg-secondary)); color: var(--text-primary); }
h1, h2, h3 { font-family: 'Outfit'; }
.app-container { display: flex; height: 100vh; overflow: hidden; }
.sidebar { width: 260px; background: rgba(255,255,255,0.03); border-right: 1px solid rgba(255,255,255,0.08); padding: 2rem; display: flex; flex-direction: column; gap: 1rem; }
.main-content { flex: 1; padding: 2rem; overflow-y: auto; }
.card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 1rem; padding: 1.5rem; }
.form-input { width: 100%; padding: 0.75rem; background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); color: white; border-radius: 0.5rem; margin-bottom: 1rem;}
.btn { padding: 0.75rem 1.5rem; border: none; border-radius: 0.5rem; cursor: pointer; color: white; background: var(--accent-primary); font-weight: 600;}
.badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 1rem; margin-right: 0.5rem; font-size: 0.875rem;}
.badge-match { background: rgba(16, 185, 129, 0.2); color: #34d399; }
.badge-miss { background: rgba(239, 68, 68, 0.2); color: #f87171; }
    """)

    create_file("frontend/src/main.jsx", "import React from 'react'; import ReactDOM from 'react-dom/client'; import App from './App'; import './index.css'; import { BrowserRouter } from 'react-router-dom'; ReactDOM.createRoot(document.getElementById('root')).render(<BrowserRouter><App /></BrowserRouter>);")

    create_file("frontend/src/App.jsx", """
import { Routes, Route, Link, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import UploadJob from './pages/UploadJob';
import ResumeAnalyzer from './pages/ResumeAnalyzer';

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const navigate = useNavigate();

  const handleLogin = (t) => { setToken(t); localStorage.setItem('token', t); navigate('/'); };
  const handleLogout = () => { setToken(null); localStorage.removeItem('token'); navigate('/'); };

  if (!token) return <Login setToken={handleLogin} />;

  return (
    <div className="app-container">
      <div className="sidebar">
        <h2>⚡ SkillPulse AI</h2>
        <Link to="/" style={{color: 'white', textDecoration: 'none'}}>📊 Dashboard</Link>
        <Link to="/jobs" style={{color: 'white', textDecoration: 'none'}}>📥 Upload Jobs CSV</Link>
        <Link to="/resume" style={{color: 'white', textDecoration: 'none'}}>🧑‍💻 Resume Analyzer</Link>
        <div style={{flex: 1}}></div>
        <button className="btn" style={{background: 'transparent', border: '1px solid white'}} onClick={handleLogout}>Logout</button>
      </div>
      <div className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/jobs" element={<UploadJob />} />
          <Route path="/resume" element={<ResumeAnalyzer />} />
        </Routes>
      </div>
    </div>
  );
}
""")

    create_file("frontend/src/pages/Login.jsx", """
import { useState } from 'react';
export default function Login({ setToken }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isRegister, setIsRegister] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const ep = isRegister ? '/api/auth/register' : '/api/auth/login';
    
    let options = {};
    if (isRegister) {
        options = { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({email, password}) };
    } else {
        const fd = new URLSearchParams(); fd.append('username', email); fd.append('password', password);
        options = { method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'}, body: fd };
    }

    try {
      const res = await fetch('http://localhost:8000' + ep, options);
      const data = await res.json();
      if (res.ok) setToken(data.access_token);
      else alert(data.detail);
    } catch { alert('Network Error'); }
  };

  return (
    <div style={{ display:'flex', justifyContent:'center', alignItems:'center', height:'100vh' }}>
      <form className="card" onSubmit={handleSubmit} style={{width: 400}}>
        <h2>{isRegister ? 'Create Account' : 'Login'}</h2>
        <input className="form-input" type="email" placeholder="Email" onChange={e=>setEmail(e.target.value)} required style={{marginTop: '1rem'}}/>
        <input className="form-input" type="password" placeholder="Password" onChange={e=>setPassword(e.target.value)} required/>
        <button className="btn" style={{width: '100%', marginBottom: '1rem'}}>{isRegister ? 'Register' : 'Login'}</button>
        <p style={{cursor:'pointer', color:'var(--accent-primary)', textAlign:'center'}} onClick={()=>setIsRegister(!isRegister)}>
          {isRegister ? 'Already have an account? Login' : 'Need an account? Register'}
        </p>
      </form>
    </div>
  );
}
""")

    create_file("frontend/src/pages/Dashboard.jsx", """
import { useState, useEffect } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export default function Dashboard() {
  const [trends, setTrends] = useState([]);
  const [forecast, setForecast] = useState({});

  useEffect(() => {
    fetch('http://localhost:8000/api/analytics/trends').then(r=>r.json()).then(setTrends);
    fetch('http://localhost:8000/api/analytics/forecast').then(r=>r.json()).then(setForecast);
  }, []);

  const fSkill = Object.keys(forecast)[0];

  return (
    <div>
      <h1 style={{marginBottom: '2rem'}}>Dashboard & Analytics</h1>
      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:'2rem'}}>
        <div className="card">
          <h2>Top Demanded Skills</h2>
          <div style={{height: 300, marginTop: '1rem'}}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={trends} layout="vertical" margin={{left: 40}}>
                <XAxis type="number" hide />
                <YAxis dataKey="skill" type="category" stroke="#fff" />
                <Tooltip />
                <Bar dataKey="count" fill="#6366f1" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="card">
          <h2>12-Month Forecast {fSkill ? `(${fSkill})` : ''}</h2>
          <div style={{height: 300, marginTop: '1rem'}}>
            {fSkill ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={forecast[fSkill]}>
                  <XAxis dataKey="month" stroke="#fff" tickFormatter={v=>v.substring(0,7)} />
                  <YAxis stroke="#fff" />
                  <Tooltip />
                  <Line type="monotone" dataKey="projected" stroke="#f59e0b" strokeWidth={3} />
                </LineChart>
              </ResponsiveContainer>
            ) : <p>No forecst data found. Upload some jobs.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
""")

    create_file("frontend/src/pages/UploadJob.jsx", """
import { useState } from 'react';

export default function UploadJob() {
  const [file, setFile] = useState(null);
  
  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    const fd = new FormData(); fd.append('file', file);
    const token = localStorage.getItem('token');
    const res = await fetch('http://localhost:8000/api/jobs/upload', {
      method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: fd
    });
    const data = await res.json();
    alert(res.ok ? data.message : "Error: " + data.detail);
  };

  return (
    <div className="card" style={{maxWidth: 600}}>
      <h2>Upload Job CSV</h2>
      <p style={{marginBottom: '1rem', color:'gray'}}>Upload CSV to extract skills into the central DB.</p>
      <form onSubmit={handleUpload}>
        <input type="file" className="form-input" accept=".csv" onChange={e=>setFile(e.target.files[0])} />
        <button className="btn">Process CSV Data</button>
      </form>
    </div>
  );
}
""")

    create_file("frontend/src/pages/ResumeAnalyzer.jsx", """
import { useState } from 'react';

export default function ResumeAnalyzer() {
  const [file, setFile] = useState(null);
  const [role, setRole] = useState('data scientist');
  const [customSkills, setCustomSkills] = useState('');
  const [results, setResults] = useState(null);
  
  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    const fd = new FormData(); 
    fd.append('file', file);
    if (role === 'custom') {
        fd.append('custom_skills', customSkills);
    } else {
        fd.append('custom_role', role);
    }

    const token = localStorage.getItem('token');
    const res = await fetch('http://localhost:8000/api/resume/analyze', {
      method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: fd
    });
    if(res.ok) setResults(await res.json());
  };

  return (
    <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:'2rem'}}>
      <div className="card">
        <h2>Resume Analyzer</h2>
        <form onSubmit={handleUpload} style={{marginTop: '1rem'}}>
          <label style={{display: 'block', marginBottom: '0.5rem'}}>Target Role / Template</label>
          <select className="form-input" value={role} onChange={e=>setRole(e.target.value)}>
             <option value="data scientist">Data Scientist</option>
             <option value="software engineer">Software Engineer</option>
             <option value="cloud architect">Cloud Architect</option>
             <option value="product manager">Product Manager</option>
             <option value="custom">-- Type Custom Required Skills --</option>
          </select>
          
          {role === 'custom' && (
             <input type="text" className="form-input" placeholder="e.g. rust, typescript, rest api"
              value={customSkills} onChange={e=>setCustomSkills(e.target.value)} required />
          )}

          <label style={{display: 'block', marginBottom: '0.5rem'}}>Upload Resume (.txt/.pdf)</label>
          <input type="file" className="form-input" accept=".txt,.pdf" onChange={e=>setFile(e.target.files[0])} />
          
          <button className="btn">Calculate Gap Score</button>
        </form>
      </div>

      {results && (
        <div className="card">
          <h2>Analysis Results</h2>
          <h1 style={{color: results.score > 50 ? 'var(--success)' : 'var(--danger)', margin: '1rem 0'}}>
            {results.score}% Match 
          </h1>
          <p style={{color: 'gray', marginBottom: '1rem'}}>Assessing profile against: {results.role_assessed}</p>
          
          <h4>✅ Matched Core Skills</h4>
          <div style={{marginBottom: '1rem', marginTop: '0.5rem'}}>
            {results.matched.map(s => <span className="badge badge-match" key={s}>{s}</span>)}
            {results.matched.length === 0 && <p style={{color:'gray'}}>None</p>}
          </div>

          <h4>❌ Missing Core Skills</h4>
          <div style={{marginBottom: '1rem', marginTop: '0.5rem'}}>
            {results.missing.map(s => <span className="badge badge-miss" key={s}>{s}</span>)}
            {results.missing.length === 0 && <p style={{color:'gray'}}>None</p>}
          </div>

          <div style={{color:'gray', fontSize: '0.875rem', marginTop: '2rem'}}>
            <i>All extracted skills detected: {results.extracted_skills.join(', ')}</i>
          </div>
        </div>
      )}
    </div>
  );
}
""")

if __name__ == "__main__":
    generate_backend()
    generate_frontend()
    print("MVP Code successfully generated.")
