import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();

    if (username === 'user' && password === 'password') {
      localStorage.setItem('authenticated', 'true');
      localStorage.setItem('username', username);
      navigate('/main');
    } else {
      setError('Invalid username or password');
    }
  };

  return (
    <form onSubmit={handleLogin}>
      <label htmlFor="username">Username</label>
      <input
        id="username"
        type="text"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        required
      />
      <label htmlFor="password">Password</label>
      <input
        id="password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      {error && <p role="alert">{error}</p>}
      <button type="submit">Login</button>
    </form>
  );
};

export default Login;
