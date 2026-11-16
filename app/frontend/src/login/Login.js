import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");


    try {
      const res = await fetch("http://localhost:8000/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if(res.ok) {
        const data = await res.json();
        localStorage.setItem('authenticated', 'true');
        localStorage.setItem('username', data.username);
        localStorage.setItem('userId', String(data.id));
        if (onLogin) onLogin(data.username);
        navigate('/main');
      } else {
        const err = await res.json();
        setError(err.detail);
      }
    } catch (err) {
      console.error(err)
      setError("Can't reach the server");
    }

  }

  return (
        <form onSubmit={handleSubmit}>
            <input placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} />
            <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} />
            <button type="submit">Login</button>
            {error && <p>{error}</p>}
        </form>
    );
}



