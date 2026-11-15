import './App.css';
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
      <img src="body.svg" usemap="#body_map"></img>
      <map name="body_map">
        <area shape="poly" coords="0,0,100,100" href="#" alt="Body Part" />
      </map>
    </div>
  )
}

function HealthBar() {
  return (
    <div className="HealthBar">
      <div className="health-bar"></div>
    </div>
  )
}

function Dashboard() {
  return (
   <div className="Dashboard">
      <Important />
      <Level2 />
      <Calendar />
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

function Important() {
  return (
    <div className="Important">
      <div className="latestUpdate">Latest Update: X hours ago</div>
      <div className="doctorRecomendations">
        <h1>Doctor Recommendations</h1>
        <ul>
          <li>Doctor Recommendation 1</li>
          <li>Doctor Recommendation 2</li>
          <li>Doctor Recommendation 3</li>
        </ul>
      </div>
      <ExportData />
    </div>
  )
}

function Level2() {
  return (
    <div className="Level2">
      <Tasks />
      <Diary />
    </div>
  )
}

function Tasks() {
  return (
    <div className="Tasks">
      <h1>Today's Tasks</h1>
      <ul>
        <li>Task 1</li>
        <li>Task 2</li>
        <li>Task 3</li>
      </ul>
    </div>
  )
}

function Diary() {
  return (
    <div className="Diary">
      <h1>Log</h1>
      <textarea placeholder="Write the log entry here. This will be shared with your healthcare provider."></textarea>
      <button>Submit</button>
    </div>
  )
}

function Calendar() {
  return (
    <div className="Calendar">
      <h1>Calendar</h1>
      <p>Calendar Component</p>
    </div>
  )
}

function ExportData() {
  return (
    <div className="ExportData">
      <h1>Export Data</h1>
      <button>Export</button>
    </div>
  )
}

export default Main;
