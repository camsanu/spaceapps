import './App.css';
import Dashboard from './Dashboard';
import { useState, useEffect } from 'react';

function Main() {
  const username = localStorage.getItem('username') || 'User';

  return (
    <div className="App">
      <Header username={username} />
      <HealthBar />
      <Body />
      <Dashboard />
    </div>
  );
}

function Header({ username }) {
  return (
    <div className="Header">
      <h1>Hello, {username}</h1>
      <DigitalClock />
    </div>
  )
}

function Body() {
  return (
    <div className="Body">
      <img src="/body.svg" width="250" height="500" useMap="#body_map" alt="Human body map" />
      <map name="body_map">
        <BodyPart name="Heart" coords="108,150,125,138,142,150,146,179,125,208,104,179" />
        <BodyPart name="Left arm muscles" coords="65,129,81,129,123,167,117,188" />
        <BodyPart name="Right arm muscles" coords="169,129,185,129,133,188,127,167" />
      </map>
    </div>
  )
}

function BodyPart({ name, coords }) {
  return (
      <area shape="poly" coords={coords} href="#" alt={name} title={name} />
  )
}

function HealthBar() {
  return (
    <div className="HealthBar">
      <div className="health-bar"></div>
    </div>
  )
}

function DigitalClock() {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => {
      setTime(new Date());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const dateString = time.toLocaleDateString('en-US', {dateStyle: 'full' });

  const timeString = time.toLocaleTimeString('en-US', {timeStyle: 'short',});

  return (
    <div className="DigitalClock">
      <p>{timeString}</p>
      <p>{dateString}</p>
    </div>
  );
}

export default Main;
