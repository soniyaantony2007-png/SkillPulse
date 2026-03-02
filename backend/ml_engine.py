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
