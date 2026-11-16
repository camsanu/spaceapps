# Create Health Monitoring Software for Astronauts on Space Missions
This is the repository containing all our codebase and files for the challenge during this NASA Space Apps Challenge 2026.  

## How to Run

The web app lives in `app/frontend`. Run:

```bash
cd app/frontend
npm install
npm start
```

`npm start` creates a project-local Python virtual environment at
`app/backend/.venv`, installs the backend dependencies there, and launches
both the React development server and FastAPI at `http://127.0.0.1:8000`.
No system Python packages are modified. Stop the command with `Ctrl+C` to
stop both servers.

For a production bundle:

```bash
cd app/frontend
npm run build
```

## Features