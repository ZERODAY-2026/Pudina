import App from "./App";
import LandingPage from "./landing/LandingPage";

export default function AppEntry() {
  const pathname = window.location.pathname.replace(/\/+$/, "") || "/";
  return pathname === "/chat" ? <App /> : <LandingPage />;
}
