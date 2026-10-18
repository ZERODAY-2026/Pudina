/**
 * src/main.tsx
 * Application entry point.
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import AppEntry from "./AppEntry";

const root = document.getElementById("root");
if (!root) throw new Error("Root element #root not found in index.html");

createRoot(root).render(
  <StrictMode>
    <AppEntry />
  </StrictMode>,
);
