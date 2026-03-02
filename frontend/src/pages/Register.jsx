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
