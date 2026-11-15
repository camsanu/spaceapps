import {useState} from 'react';
import Calendar from 'react-calendar';
import './App.css';
import 'react-calendar/dist/Calendar.css';

function Dashboard() {
  return (
   <div className="Dashboard">
      <Important />
      <Level2 />
      <Calendar />
    </div>
  )
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

function ExportData() {
  return (
    <div className="ExportData">
      <h1>Export Data</h1>
      <button>Export</button>
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
      <textarea id="diary-textarea" placeholder="Write the log entry here. This will be shared with your healthcare provider."></textarea>
      <button onClick={saveLogToFile}>Submit</button>
    </div>
  )
}

function saveLogToFile() {
  const logContent = document.getElementById('diary-textarea').value;
  if (logContent.trim() === '') {
    alert('Please enter some text before submitting.');
    return;
  }

  const blob = new Blob([logContent], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const dateString = new Date().toISOString().split('T')[0];
  const a = document.createElement('a');
  a.href = url;
  a.download = `log_${dateString}.txt`;
  document.body.appendChild(a);
  a.click();
  
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function CalendarContainer() {
  const [date, setDate] = useState(new Date());
  return (
    <div className="Calendar">
      <Calendar onChange={setDate} value={date} />
      <button>Set Scheduled Regular Check Up</button>
    </div>
  )
}

export default Dashboard;