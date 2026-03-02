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
