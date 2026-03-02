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
   source venv/bin/activate  # On Windows: venv\Scripts\activate
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
