import logo from './logo.svg';
import './App.css';

function Main() {
  return (
    <div className="App">
      <Header />
      <HealthBar />
      <Body />
      <Dashboard />
      <ExportData />
    </div>
  );
}

function Header() {
  return (
    <div className="Header">
      <h1>Hello, name</h1>
      <p>Hours:Minute:Seconds, Weekday, Month, Year</p>
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
      <h1>Health Bar</h1>
      <div class="health-bar">Health Bar</div>
    </div>
  )
}

function Dashboard() {
  return (
   <div className="Dashboard">
      <h1>Dashboard</h1>
      <Important />
      <Tasks />
      <Diary />
      <Calendar />
    </div>
  )
}

function Important() {
  return (
    <div className="Important">
      <div className="latestUpdate">Latest Update: X hours ago</div>
      <div className="doctorReccomendations">
        <ul>
          <li>Doctor Recommendation 1</li>
          <li>Doctor Recommendation 2</li>
          <li>Doctor Recommendation 3</li>
        </ul>
      </div>
      <div className="generalInfo">
        <p>General Info</p>
      </div>
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
      <h1>Diary</h1>
      <textarea placeholder="Write your diary entry here..."></textarea>
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
