import { useNavigate } from "react-router-dom";
import HealthDashboard from "./HealthDashboard";

function logout() {
  ["authenticated", "username", "userId"].forEach((k) => localStorage.removeItem(k));
  window.location.assign("/login"); // full reload so every auth check starts fresh
}

export default function HealthPage() {
  const navigate = useNavigate();
  const userId = Number(localStorage.getItem("userId"));

  // Logged in before this update, so we don't know the user's id yet: log in once more.
  if (!userId) {
    return (
      <div style={{ padding: 24 }}>
        <p>Please log in again so the health data can be loaded for your account.</p>
        <button className="widget-button" onClick={logout}>Go to login</button>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
                    maxWidth: 1280, margin: "0 auto", padding: "24px 24px 0" }}>
        <button className="widget-button" onClick={() => navigate("/main")}>← Back to home</button>
        <button className="text-button" onClick={logout}>Log out</button>
      </div>
      <HealthDashboard apiBase="http://localhost:8000" userId={userId} />
    </div>
  );
}
