import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import re
import datetime
import io

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

# ==========================================
# CONFIG & STATE
# ==========================================
st.set_page_config(page_title="SkillPulse AI Platform", layout="wide", page_icon="⚡")

# Initialize Session States
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.users = {"demo": "demo123"} # Mock DB
    
    # Mock Historical Data
    dates = pd.date_range(end=datetime.date.today(), periods=24, freq='M')
    skills_hist = {
        "Python": np.linspace(50, 100, 24) + np.random.normal(0, 5, 24),
        "SQL": np.linspace(60, 90, 24) + np.random.normal(0, 3, 24),
        "AWS": np.linspace(30, 85, 24) + np.random.normal(0, 6, 24),
        "React": np.linspace(40, 75, 24) + np.random.normal(0, 4, 24),
        "Machine Learning": np.linspace(20, 95, 24) + np.random.normal(0, 8, 24)
    }
    df_hist = pd.DataFrame(skills_hist)
    df_hist['Month'] = dates
    st.session_state.trend_data = df_hist

# Master list of skills for our NLP keyword extractor
KNOWN_SKILLS = [
    "python", "java", "sql", "aws", "react", "machine learning", "deep learning", 
    "nlp", "kubernetes", "docker", "javascript", "typescript", "c++", "c#", 
    "golang", "rust", "azure", "gcp", "agile", "scrum", "tensorflow", "pytorch",
    "pandas", "scikit-learn", "data analysis", "tableau", "power bi", "hadoop", "spark"
]

ROLES_REQUIREMENTS = {
    "Data Scientist": ["python", "machine learning", "sql", "pandas", "scikit-learn", "tensorflow", "nlp"],
    "Software Engineer": ["python", "java", "javascript", "react", "sql", "docker", "aws"],
    "Cloud Architect": ["aws", "azure", "gcp", "kubernetes", "docker", "python"],
    "Product Manager": ["agile", "scrum", "data analysis", "sql", "tableau"]
}

# ==========================================
# AUTHENTICATION
# ==========================================
def auth_sidebar():
    st.sidebar.title("⚡ SkillPulse AI")
    if not st.session_state.logged_in:
        st.sidebar.subheader("Account Access")
        
        tab1, tab2 = st.sidebar.tabs(["Login", "Sign Up"])
        with tab1:
            user = st.text_input("Username", key="login_user")
            pwd = st.text_input("Password", type="password", key="login_pwd")
            if st.button("Login"):
                if user in st.session_state.users and st.session_state.users[user] == pwd:
                    st.session_state.logged_in = True
                    st.session_state.username = user
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please try again.")
        with tab2:
            new_user = st.text_input("New Username", key="signup_user")
            new_pwd = st.text_input("New Password", type="password", key="signup_pwd")
            if st.button("Sign Up"):
                if new_user and new_pwd:
                    if new_user in st.session_state.users:
                        st.error("Username already exists!")
                    else:
                        st.session_state.users[new_user] = new_pwd
                        st.success("Account created! Please log in.")
                else:
                    st.error("Please provide both username and password.")
    else:
        st.sidebar.success(f"Welcome back, {st.session_state.username}!")
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()

# ==========================================
# NLP HELPER
# ==========================================
def extract_skills(text):
    text = text.lower()
    # Simple regex word boundary matching for NLP extraction
    extracted = []
    for skill in KNOWN_SKILLS:
        # handle skills with special chars like c++
        escaped_skill = re.escape(skill)
        pattern = r'\b' + escaped_skill + r'\b'
        if re.search(pattern, text):
            extracted.append(skill)
    return list(set(extracted))

def read_pdf(file):
    if PyPDF2 is None:
        return "ERROR_NO_PYPDF2"
    try:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + " "
        return text
    except Exception as e:
        return ""

# ==========================================
# PAGES
# ==========================================
def page_dashboard():
    st.title("📊 Platform Analytics Dashboard")
    st.markdown("Overview of dynamic tech skill demands based on platform ingestion data.")
    
    df = st.session_state.trend_data
    latest = df.drop(columns=['Month']).iloc[-1]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Skills Tracked", len(latest), "Active DB")
    col2.metric("Top Skill Today", latest.idxmax(), f"{latest.max():.1f} Index Score")
    col3.metric("Fastest Growing", "Machine Learning", "+15% MoM")
    
    st.markdown("---")
    st.subheader("Historical Skill Demand Trends")
    st.line_chart(df.set_index('Month'))

def page_data_ingestion():
    st.title("📥 Job Listing Ingestion")
    st.markdown("Upload a CSV file containing job listings to extract technical skills using NLP.")
    
    st.info("The CSV should contain a column named `Description`, `Job Description`, or similar.")
    
    uploaded_file = st.file_uploader("Upload Job CSV", type=['csv'])
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.write("**Preview of Uploaded Data:**")
            st.dataframe(df.head(3))
            
            # Autodetect description column
            desc_col = None
            for col in df.columns:
                if 'desc' in col.lower() or 'summary' in col.lower() or 'text' in col.lower():
                    desc_col = col
                    break
            
            if st.button("Run NLP Pipeline", type="primary"):
                if desc_col:
                    with st.spinner("Executing Named Entity Recognition for Skills..."):
                        all_skills = []
                        for text in df[desc_col].dropna():
                            extracted = extract_skills(str(text))
                            all_skills.extend(extracted)
                        
                        if all_skills:
                            skill_counts = pd.Series(all_skills).value_counts()
                            st.success(f"Successfully processed {len(df)} records. Found {len(skill_counts)} unique skills!")
                            
                            st.subheader("Extracted Skill Occurrences")
                            st.bar_chart(skill_counts)
                            
                            # Update global mock data
                            st.info("In a full production environment, these frequencies would be stored in the central time-series database.")
                        else:
                            st.warning("No known technical skills were extracted from this dataset.")
                else:
                    st.error("No suitable text/description column detected in the CSV.")
        except Exception as e:
            st.error(f"Error reading CSV: {str(e)}")

def page_forecasting():
    st.title("🔮 Predictive Demand Forecasting")
    st.markdown("Machine Learning powered 12-month projections of skill market value.")
    
    df = st.session_state.trend_data
    skills_available = [c for c in df.columns if c != 'Month']
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Parameters")
        selected_skill = st.selectbox("Select Target Skill", skills_available)
        st.write("Model: `Linear Regression`")
        st.write("Horizon: `12 Months`")
        run_model = st.button("Generate Forecast", type="primary", use_container_width=True)
    
    with col2:
        if run_model:
            with st.spinner("Training predictive model..."):
                # Prepare data
                X = np.arange(len(df)).reshape(-1, 1)
                y = df[selected_skill].values
                
                # Train Model
                model = LinearRegression()
                model.fit(X, y)
                
                # Predict next 12 months
                future_X = np.arange(len(df), len(df) + 12).reshape(-1, 1)
                future_y = model.predict(future_X)
                
                # Generate Dates
                last_date = df['Month'].iloc[-1]
                future_dates = [last_date + pd.DateOffset(months=i) for i in range(1, 13)]
                
                # Visualization
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.plot(df['Month'], y, label='Historical Demand', marker='o', color='#4b4bf6', linewidth=2)
                ax.plot(future_dates, future_y, label='12-Month Projections', marker='x', linestyle='--', color='#f59e0b', linewidth=2)
                
                ax.set_title(f"Demand Trajectory: {selected_skill}")
                ax.set_ylabel("Market Demand Index")
                ax.grid(True, linestyle='--', alpha=0.5)
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                ax.legend()
                
                st.pyplot(fig)
                
                # Growth Calculation
                growth = future_y[-1] - df[selected_skill].iloc[-1]
                pct_growth = (growth / df[selected_skill].iloc[-1]) * 100
                
                st.markdown("### Model Insights")
                if growth > 0:
                    st.success(f"**Positive Trend:** The model projects `{selected_skill}` demand will grow by **{pct_growth:.1f}%** over the next year.")
                else:
                    st.warning(f"**Negative Trend:** The model projects `{selected_skill}` demand will decline over the next year.")

def page_analyzer():
    st.title("🧑‍💻 Resume Analysis & Gap Score")
    st.markdown("Upload your resume to instantly calculate your personalized skill gap against industry roles.")
    
    target_role = st.selectbox("Select Your Target Role", list(ROLES_REQUIREMENTS.keys()))
    
    resume_file = st.file_uploader("Upload Resume Document", type=['txt', 'pdf'])
    
    if resume_file:
        if st.button("Calculate Readiness Score", type="primary"):
            with st.spinner("Passing document through NLP extraction engine..."):
                file_ext = resume_file.name.split('.')[-1].lower()
                text = ""
                
                if file_ext == 'txt':
                    text = resume_file.read().decode('utf-8', errors='ignore')
                elif file_ext == 'pdf':
                    text = read_pdf(resume_file)
                    if text == "ERROR_NO_PYPDF2":
                        st.error("Cannot process PDF resumes. The `PyPDF2` package is not installed. Please upload a TXT file instead or contact administration.")
                        return
                        
                if not text.strip():
                    st.warning("No readable text could be extracted from this document.")
                    return
                
                # Process
                user_skills = extract_skills(text)
                required = ROLES_REQUIREMENTS[target_role]
                
                matched = [s for s in required if s in user_skills]
                missing = [s for s in required if s not in user_skills]
                
                score = (len(matched) / len(required) * 100) if required else 0
                
                # Results UI
                st.markdown("---")
                colA, colB = st.columns([1,2])
                with colA:
                    st.metric("Overall Readiness Score", f"{score:.0f}%")
                    st.progress(score / 100)
                with colB:
                    st.write(f"**Detected Technical Skills:** `{len(user_skills)}`")
                    st.write(", ".join([f"{s.title()}" for s in user_skills]) if user_skills else "*No supported tech skills identified.*")
                
                st.markdown("---")
                st.subheader("Skill Gap Breakdown")
                col3, col4 = st.columns(2)
                
                with col3:
                    st.success(f"✅ Verified Core Skills ({len(matched)})")
                    for s in matched:
                        st.write(f"- {s.title()}")
                    if not matched:
                        st.write("*None*")
                
                with col4:
                    st.error(f"❌ Missing Core Skills ({len(missing)})")
                    for s in missing:
                        st.write(f"- {s.title()}")
                    if not missing:
                        st.write("*Your profile perfectly matches this role!*")
                        
                if missing:
                    st.info(f"💡 **AI Suggestion**: Focus your learning efforts on **{missing[0].title()}** to maximize your match rate for the {target_role} role.")

# ==========================================
# APP ROUTING
# ==========================================
def main():
    auth_sidebar()
    
    if not st.session_state.logged_in:
        st.markdown(
            """
            <div style="text-align: center; padding: 50px;">
                <h1 style="font-size: 3rem; margin-bottom: 0;">⚡ SkillPulse AI</h1>
                <h3 style="color: gray; margin-top: 5px;">Skill Demand Intelligence Platform</h3>
            </div>
            """, unsafe_allow_html=True
        )
        st.info("👋 Hello! Please use the sidebar to log in or create a new account to access the platform.")
        
        st.markdown("""
        ### Platform Features:
        - **📥 Job Ingestion**: Upload CSVs and extract trending tech skills natively using NLP.
        - **📊 Analytics Dashboard**: View live demand trends for modern technology stacks.
        - **🔮 Predictive Forecasting**: Machine Learning models projecting 12-month future role demands.
        - **🧑‍💻 Resume Analysis**: Upload your CV/Resume to instantly calculate your Skill Gap Score against targeted roles.
        """)
        
        st.write("\n\n*Note: Use `demo` / `demo123` to log in instantly if you don't want to create an account.*")
        return
        
    st.sidebar.markdown("---")
    page = st.sidebar.radio("🧭 Navigation Menu", [
        "📊 Analytics Dashboard",
        "📥 Data Ingestion (Jobs)",
        "🔮 Demand Forecasting",
        "🧑‍💻 Resume Analyzer"
    ])
    
    if page == "📊 Analytics Dashboard":
        page_dashboard()
    elif page == "📥 Data Ingestion (Jobs)":
        page_data_ingestion()
    elif page == "🔮 Demand Forecasting":
        page_forecasting()
    elif page == "🧑‍💻 Resume Analyzer":
        page_analyzer()

if __name__ == "__main__":
    main()
