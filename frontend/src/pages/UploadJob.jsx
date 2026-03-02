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
