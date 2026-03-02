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
