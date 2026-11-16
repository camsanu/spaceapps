import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "./Login";
import Main from "./components/Main";
import HealthPage from "./components/HealthPage";

function isAuthenticated() {
  return localStorage.getItem("authenticated") === "true";
}

function RequireAuth({ children }) {
  return isAuthenticated() ? children : <Navigate to="/login" replace />;
}

// These re-check localStorage every time they mount, so logging out / in takes effect immediately.
function PublicOnly({ children }) {
  return isAuthenticated() ? <Navigate to="/main" replace /> : children;
}

function Home() {
  return <Navigate to={isAuthenticated() ? "/main" : "/login"} replace />;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={<PublicOnly><Login /></PublicOnly>}
        />
        <Route
          path="/main"
          element={
            <RequireAuth>
              <Main />
            </RequireAuth>
          }
        />
        <Route
          path="/health"
          element={
            <RequireAuth>
              <HealthPage />
            </RequireAuth>
          }
        />
        <Route path="/" element={<Home />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;