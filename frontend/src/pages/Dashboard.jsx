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
