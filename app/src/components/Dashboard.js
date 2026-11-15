import {useState, useEffect, useId, useRef } from 'react';
import Calendar from 'react-calendar';
import './App.css';
import 'react-calendar/dist/Calendar.css';

function Dashboard() {
  return (
   <main className="Dashboard">
      <Important />
      <Level2 />
      <CalendarContainer />
    </main>
  )
}

function Important() {
  return (
    <section className="Important widget-card widget-card--featured">
      <div className="latestUpdate widget-label">Latest Update: X hours ago</div>
      <div className="doctorRecomendations widget-card__section">
        <div className="widget-section-header">
          <h2>Doctor Recommendations</h2>
          <WidgetActionButton />
        </div>
        <ul className="todo-list">
          <li className="todo-item">Doctor Recommendation 1</li>
          <li className="todo-item">Doctor Recommendation 2</li>
          <li className="todo-item">Doctor Recommendation 3</li>
        </ul>
      </div>
      <Stats />
    </section>
  )
}

function Stats() {
  return (
    <section className="Stats widget-card">
      <div className="widget-section-header">
        <h2>General stats</h2>
        <WidgetActionButton />
      </div>
      <ul className="stats-list">
        <li><span>Heart rate</span><strong>72 bpm</strong></li>
        <li><span>Sleep</span><strong>7h 42m</strong></li>
        <li><span>Activity</span><strong>6,240 steps</strong></li>
        <li><span>Last check-in</span><strong>Today</strong></li>
      </ul>
    </section>
  )
}

const [show, setShow] = useState(false);

function WidgetActionButton({ onClick }) {
  return (
    <button className="text-button" type="button" onClick={() => setShow(true)}>
      See more
    </button>
  )
}

function PopUp({ show, close, children }) {
  if (!show) {return null}
  return (
    <div className="popup">
      <button className="popup-close" onClick={close}>Close</button>
      <div className="popup-content">
        {children}
      </div>
    </div>
  );
}

function Level2() {
  return (
    <section className="Level2">
      <Tasks />
      <Diary />
    </section>
  )
}

function Tasks() {
  return (
    <div className="Tasks widget-card">
      <h2>Today's Tasks</h2>
      <ul className="todo-list">
        <li className="todo-item">Task 1</li>
        <li className="todo-item">Task 2</li>
        <li className="todo-item">Task 3</li>
      </ul>
    </div>
  )
}

function Diary() {
  return (
    <div className="Diary widget-card">
      <h2>Log</h2>
      <div className="Diary-input">
        <textarea id="diary-textarea" placeholder="Write the log entry here. This will be shared with your healthcare provider."></textarea>
        <button className="submit-button" onClick={saveLogToFile} aria-label="Submit log"><img src="submit-icon.png" alt="" width="16" height="16" /></button>
      </div>
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
  const [scheduledDate, setScheduledDate] = useState(null);

  return (
    <section className="Calendar widget-card">
      <div className="calendar-header">
        <div>
          <h2>Schedule check-up</h2>
        </div>
        <button
          className="calendar-icon"
          onClick={() => setScheduledDate(date)}
          aria-label="Schedule regular check-up"
        >
          +
        </button>
      </div>
      <Calendar
        onChange={setDate}
        value={date}
        tileClassName={({ date: tileDate, view }) =>
          view === 'month' && scheduledDate &&
          tileDate.toDateString() === scheduledDate.toDateString()
            ? 'scheduled-tile'
            : null
        }
      />
    </section>
  )
}

export default Dashboard;