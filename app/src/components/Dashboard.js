import {useState} from 'react';
import Calendar from 'react-calendar';
import './App.css';
import 'react-calendar/dist/Calendar.css';

function Dashboard({ tasks, onTaskComplete }) {
  return (
   <main className="Dashboard">
      <Important />
      <Level2 tasks={tasks} onTaskComplete={onTaskComplete} />
      <CalendarContainer />
    </main>
  )
}

function Important() {
  const [showRecommendations, setShowRecommendations] = useState(false);

  return (
    <section className="Important widget-card widget-card--featured">
      <div className="latestUpdate widget-label">Latest Update: X hours ago</div>
      <div className="doctorRecomendations widget-card__section">
        <div className="widget-section-header">
          <h2>Doctor Recommendations</h2>
          <WidgetActionButton onClick={() => setShowRecommendations(true)} />
        </div>
        <ul className="todo-list">
          <li className="todo-item">Doctor Recommendation 1</li>
          <li className="todo-item">Doctor Recommendation 2</li>
          <li className="todo-item">Doctor Recommendation 3</li>
        </ul>
      </div>
      <Stats />
      <PopUp
        show={showRecommendations}
        close={() => setShowRecommendations(false)}
        title="Doctor Recommendations"
      >
        <ul className="todo-list">
          <li className="todo-item">Doctor Recommendation 1</li>
          <li className="todo-item">Doctor Recommendation 2</li>
          <li className="todo-item">Doctor Recommendation 3</li>
        </ul>
      </PopUp>
    </section>
  )
}

function Stats() {
  const [showStats, setShowStats] = useState(false);

  return (
    <section className="Stats widget-card">
      <div className="widget-section-header">
        <h2>General stats</h2>
        <WidgetActionButton onClick={() => setShowStats(true)} />
      </div>
      <ul className="stats-list">
        <li><span>Heart rate</span><strong>72 bpm</strong></li>
        <li><span>Sleep</span><strong>7h 42m</strong></li>
        <li><span>Activity</span><strong>6,240 steps</strong></li>
        <li><span>Last check-in</span><strong>Today</strong></li>
      </ul>
      <PopUp show={showStats} close={() => setShowStats(false)} title="General stats">
        <ul className="stats-list">
          <li><span>Heart rate</span><strong>72 bpm</strong></li>
          <li><span>Sleep</span><strong>7h 42m</strong></li>
          <li><span>Activity</span><strong>6,240 steps</strong></li>
          <li><span>Last check-in</span><strong>Today</strong></li>
        </ul>
      </PopUp>
    </section>
  )
}

function WidgetActionButton({ onClick }) {
  return (
    <button className="text-button" type="button" onClick={onClick}>
      See more
    </button>
  )
}

function PopUp({ show, close, title, children }) {
  if (!show) {return null}
  return (
    <div className="popup" role="dialog" aria-modal="true" aria-label={title}>
      <div className="popup-content">
        <div className="popup-header">
          <h2>{title}</h2>
          <button className="popup-close" onClick={close} aria-label="Close popup">×</button>
        </div>
        {children}
      </div>
    </div>
  );
}

function Level2({ tasks, onTaskComplete }) {
  return (
    <section className="Level2">
      <Tasks tasks={tasks} onTaskComplete={onTaskComplete} />
      <Diary />
    </section>
  )
}

function Tasks({ tasks, onTaskComplete }) {
  const [selectedTask, setSelectedTask] = useState(null);

  return (
    <div className="Tasks widget-card">
      <h2>Today's Tasks</h2>
      <ul className="todo-list">
        {tasks.map((task) => (
          <li className="todo-item" key={task.id}>
            <input
              type="checkbox"
              id={task.id}
              onChange={() => onTaskComplete(task.id)}
            />
            <label htmlFor={task.id}>{task.label}</label>
            <button
              className="info-button"
              type="button"
              aria-label={`More information about ${task.label}`}
              onClick={() => setSelectedTask(task)}
            >
              ?
            </button>
          </li>
        ))}
      </ul>
      {tasks.length === 0 && (
        <p className="tasks-complete">All tasks complete!</p>
      )}
      <PopUp
        show={selectedTask !== null}
        close={() => setSelectedTask(null)}
        title={selectedTask ? selectedTask.label : 'Task information'}
      >
        {selectedTask && (
          <div className="task-details">
            <p>{selectedTask.label} is part of today's health routine.</p>
            <p>You should complete it because it contributes to your overall health and well-being.</p>
            <p>Mark it complete when you are finished.</p>
          </div>
        )}
      </PopUp>
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