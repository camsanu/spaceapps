import './App.css';
import Dashboard from './Dashboard';
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

function Main() {
  const username = localStorage.getItem('username') || 'User';
  const [tasks, setTasks] = useState([
    { id: 'task1', label: 'Task 1' },
    { id: 'task2', label: 'Task 2' },
    { id: 'task3', label: 'Task 3' },
  ]);
  const totalTasks = 3;
  const progress = (totalTasks - tasks.length) / totalTasks;

  function completeTask(taskId) {
    setTasks((currentTasks) => currentTasks.filter((task) => task.id !== taskId));
  }

  function BodyStatus() {
    if (progress === 0) {
      return ('╥‸╥');
    } else if (progress < 1) {
      return (`↼_↼`);
    } else {
      return ('•‿•');
    }
  }

  return (
    <div className="App">
      <Header username={username} />
      <HealthBar progress={progress} />
      <Body status={BodyStatus()} />
      <Dashboard tasks={tasks} onTaskComplete={completeTask} />
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

function Body({ status }) {
  return (
    <div className="Body">
      <div className="body-status">{status}</div>
      <img src="/body.svg" width="180" height="543" useMap="#body_map" alt="Human body map" />
      <map name="body_map">
        <BodyPart name="Heart" coords="108,150,125,138,142,150,146,179,125,208,104,179" />
        <BodyPart name="Left arm muscles" coords="65,129,81,129,123,167,117,188" />
        <BodyPart name="Right arm muscles" coords="169,129,185,129,133,188,127,167" />
      </map>
      <ExportData />
      <AnalyticsLink />
    </div>
  )
}

function AnalyticsLink() {
  const navigate = useNavigate();
  return (
    <div className="ExportData widget-card">
      <h2>Health analytics</h2>
      <button className="widget-button" onClick={() => navigate('/health')}>Open</button>
    </div>
  )
}

function ExportData() {
  return (
    <div className="ExportData widget-card">
      <h2>Export Data</h2>
      <button className="widget-button" onClick={exportData}>Export</button>
    </div>
  )
}

function exportData() {
  const data = 'Health data export';
  const url = URL.createObjectURL(new Blob([data], {type: 'text/plain'}));
  const link = document.createElement('a');
  link.href = url;
  link.download = `health-data-${new Date().toISOString().split('T')[0]}.txt`;
  link.click();
  URL.revokeObjectURL(url);
}

function BodyPart({ name, coords }) {
  return (
      <area shape="poly" coords={coords} href="#" alt={name} title={name} />
  )
}

function HealthBar({ progress }) {
  return (
    <div className="HealthBar">
      <div className="health-bar" style={{height: `${progress * 100}%`}}></div>
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

  const timeString = time.toLocaleTimeString('en-US', {timeStyle: 'short',});

  return (
    <div className="DigitalClock">
      <p>{timeString}</p>
    </div>
  );
}

export default Main;
