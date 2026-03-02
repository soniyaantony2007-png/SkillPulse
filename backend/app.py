import os
import io
import datetime
import pandas as pd
from dateutil import parser
import string
import numpy as np
from sklearn.linear_model import LinearRegression

from flask import Flask, request, jsonify
from flask_cors import CORS

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Date, ForeignKey, Float, func
from sqlalchemy.orm import declarative_base, sessionmaker

import bcrypt
from jose import JWTError, jwt

# --- CONFIG & DB ---
DATABASE_URL = "sqlite:///./skillpulse.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

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

# --- AUTH ---
SECRET_KEY = "mvp-secret-key-change-in-prod"
ALGORITHM = "HS256"

def verify_password(plain_password, hashed_password):
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=60*24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None

# --- ML ENGINE ---
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
    text_prepared = " " + text.translate(str.maketrans('', '', string.punctuation)) + " "
    return [skill for skill in PREDEFINED_SKILLS if f" {skill} " in text_prepared]

def train_forecasts(db):
    jobs = db.query(Job).all()
    job_skills = db.query(JobSkill).all()
    if not jobs or not job_skills: return
        
    df_jobs = pd.DataFrame([{"job_id": j.id, "month": j.date_posted.replace(day=1)} for j in jobs])
    df_js = pd.DataFrame([{"job_id": js.job_id, "skill_id": js.skill_id} for js in job_skills])
    
    df = pd.merge(df_js, df_jobs, on="job_id")
    monthly_counts = df.groupby(['skill_id', 'month']).size().reset_index(name='count')
    
    db.query(Forecast).delete()
    
    for skill_id in monthly_counts['skill_id'].unique():
        skill_data = monthly_counts[monthly_counts['skill_id'] == skill_id].sort_values('month')
        if len(skill_data) < 2: continue
            
        months_numeric = np.arange(len(skill_data)).reshape(-1, 1)
        counts = skill_data['count'].values
        
        model = LinearRegression()
        model.fit(months_numeric, counts)
        last_month = skill_data['month'].iloc[-1]
        
        for i in range(1, 13):
            try: pred_month = last_month + pd.DateOffset(months=i)
            except: continue
            pred_demand = max(0, model.predict([[len(skill_data) - 1 + i]])[0])
            db.add(Forecast(skill_id=skill_id, month=pred_month.date(), projected_demand=pred_demand))
            
    db.commit()

# --- APP ---
app = Flask(__name__)
CORS(app)

@app.before_request
def before_request():
    request.db = SessionLocal()

@app.teardown_request
def teardown_request(exception):
    db = getattr(request, 'db', None)
    if db is not None: db.close()

def require_auth():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    return get_current_user(auth_header.split(' ')[1])

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    if request.db.query(User).filter(User.email == data.get('email')).first():
        return jsonify({"detail": "Email already registered"}), 400
    
    new_user = User(email=data['email'], hashed_password=get_password_hash(data['password']))
    request.db.add(new_user)
    request.db.commit()
    return jsonify({"access_token": create_access_token({"sub": new_user.email}), "token_type": "bearer"})

@app.route('/api/auth/login', methods=['POST'])
def login():
    email = request.form.get('username') or request.json.get('email')
    password = request.form.get('password') or request.json.get('password')
    user = request.db.query(User).filter(User.email == email).first()
    
    if not user or not verify_password(password, user.hashed_password):
        return jsonify({"detail": "Incorrect email or password"}), 401
    
    return jsonify({"access_token": create_access_token({"sub": user.email}), "token_type": "bearer"})

@app.route('/api/jobs/upload', methods=['POST'])
def upload_jobs():
    if not require_auth(): return jsonify({"detail": "Unauthorized"}), 401
    file = request.files.get('file')
    if not file or not file.filename.endswith('.csv'):
        return jsonify({"detail": "Only CSV files are supported"}), 400
    
    df = pd.read_csv(file)
    desc_col = next((c for c in df.columns if 'desc' in c.lower() or 'text' in c.lower()), None)
    title_col = next((c for c in df.columns if 'title' in c.lower() or 'role' in c.lower()), None)
    
    if not desc_col: return jsonify({"detail": "Cannot find description column"}), 400
        
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
        request.db.add(new_job)
        request.db.flush()
        
        skills = extract_skills_from_text(desc)
        for s in skills:
            skill_db = request.db.query(Skill).filter(Skill.name == s).first()
            if not skill_db:
                skill_db = Skill(name=s)
                request.db.add(skill_db)
                request.db.flush()
            request.db.add(JobSkill(job_id=new_job.id, skill_id=skill_db.id))
        jobs_added += 1
        
    request.db.commit()
    train_forecasts(request.db)
    return jsonify({"message": f"Ingested {jobs_added} jobs."})

@app.route('/api/analytics/trends', methods=['GET'])
def get_trends():
    query = (
        request.db.query(Skill.name, func.count(JobSkill.job_id).label("count"))
        .join(JobSkill, Skill.id == JobSkill.skill_id)
        .group_by(Skill.name)
        .order_by(func.count(JobSkill.job_id).desc())
        .limit(10)
    )
    return jsonify([{"skill": r.name, "count": r.count} for r in query.all()])

@app.route('/api/analytics/forecast', methods=['GET'])
def get_forecast():
    forecasts = request.db.query(Forecast).all()
    skills = {s.id: s.name for s in request.db.query(Skill).all()}
    res = {}
    for f in forecasts:
        s_name = skills[f.skill_id]
        if s_name not in res: res[s_name] = []
        res[s_name].append({"month": f.month.isoformat(), "projected": float(f.projected_demand)})
    return jsonify(res)

@app.route('/api/resume/analyze', methods=['POST'])
def analyze_resume():
    if not require_auth(): return jsonify({"detail": "Unauthorized"}), 401
    file = request.files.get('file')
    if not file: return jsonify({"detail": "No file uploaded"}), 400
    
    custom_role = request.form.get('custom_role')
    custom_skills = request.form.get('custom_skills')
    
    text = ""
    if file.filename.endswith(".pdf"):
        import PyPDF2
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages: text += page.extract_text() + " "
    else:
        text = file.read().decode('utf-8', errors='ignore')
        
    user_skills = extract_skills_from_text(text)
    
    target_skills = []
    if custom_role and custom_role.lower() in ROLE_ARCHETYPES:
        target_skills = list(ROLE_ARCHETYPES[custom_role.lower()])
    elif custom_skills:
        target_skills = [s.strip().lower() for s in custom_skills.split(',') if s.strip()]
    else:
        top = request.db.query(Skill.name).join(JobSkill).group_by(Skill.name).order_by(func.count(JobSkill.job_id).desc()).limit(7).all()
        target_skills = [r.name for r in top] if top else ["python", "sql", "aws", "react", "machine learning"]

    matched = [s for s in target_skills if s in user_skills]
    missing = [s for s in target_skills if s not in user_skills]
    score = int((len(matched) / len(target_skills)) * 100) if target_skills else 0
    
    return jsonify({
        "score": score,
        "matched": matched,
        "missing": missing,
        "extracted_skills": user_skills,
        "role_assessed": custom_role or "General Market Top Skills"
    })

if __name__ == '__main__':
    app.run(port=8000, debug=True)
