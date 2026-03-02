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
