"use client";
import { motion } from "framer-motion";
import RippleGrid from "./components/RippleGrid";
import FloatingNavbar from "./components/FloatingNavbar";
import MagicBento from "./components/MagicBento";
import PipelineSteps from "./components/PipelineSteps";
import "./landing.css";
import {
  Database,
  ShieldCheck,
  Activity,
  ArrowRight,
  ExternalLink,
  Cpu,
} from "lucide-react";

export default function Home() {
  return (
    <main
      className="landing-page"
      style={{
        minHeight: "100vh",
        backgroundColor: "#090D0B",
        width: "100%",
        color: "#ECFDF5",
        overflowX: "hidden",
      }}
    >
      <FloatingNavbar />

      {/* --- Top Section: Hero + Ripple Grid --- */}
      <section
        style={{
          position: "relative",
          width: "100%",
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          overflow: "hidden",
          paddingTop: "4rem",
        }}
      >
        {/* Ripple Grid Animated WebGL Background */}
        <div style={{ position: "absolute", inset: 0, zIndex: 0 }}>
          <RippleGrid
            enableRainbow={false}
            gridColor="#10b981"
            rippleIntensity={0.045}
            gridSize={12}
            gridThickness={16}
            mouseInteraction={true}
            mouseInteractionRadius={1.3}
            opacity={0.35}
            fadeDistance={1.4}
          />
        </div>

        {/* Ambient Top Glow */}
        <div
          style={{
            position: "absolute",
            top: "-15%",
            left: "50%",
            transform: "translateX(-50%)",
            width: "60vw",
            height: "450px",
            background:
              "radial-gradient(ellipse at center, rgba(16, 185, 129, 0.18) 0%, transparent 70%)",
            filter: "blur(60px)",
            pointerEvents: "none",
            zIndex: 0,
          }}
        />

        {/* Hero Content */}
        <div
          className="landing-container"
          style={{ position: "relative", zIndex: 1, margin: "0 auto" }}
        >
          <motion.div
            className="hero-section"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            {/* Top Pill Badge */}
            <motion.div
              className="badge-pill"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2 }}
            >
              <Cpu size={14} /> Enterprise Snowflake Intelligence
            </motion.div>

            {/* Main Title */}
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.35 }}
            >
              DataMind
            </motion.h1>

            {/* Subtitle */}
            <motion.p
              className="subtitle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              Conversational Intelligence for Snowflake Datasets
            </motion.p>

            {/* Status Pills */}
            <motion.div
              className="status-pills"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.65 }}
            >
              {[
                { label: "Snowflake Read-Only", color: "#10B981" },
                { label: "Gemma 3 Powered", color: "#34D399" },
                { label: "SQL Guard Protected", color: "#F59E0B" },
                { label: "Live Snowflake Results", color: "#14B8A6" },
              ].map((p, i) => (
                <motion.span
                  key={i}
                  className="pill"
                  whileHover={{
                    scale: 1.05,
                    backgroundColor: "rgba(20, 30, 25, 0.9)",
                    borderColor: p.color,
                  }}
                  whileTap={{ scale: 0.95 }}
                >
                  <span className="dot" style={{ backgroundColor: p.color }} />
                  {p.label}
                </motion.span>
              ))}
            </motion.div>

            {/* Description */}
            <motion.p
              className="description"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.8 }}
            >
              Transform your natural-language questions into vetted, read-only
              Snowflake SQL. Get instant analytical answers with full query
              lineage, row explanations, and transparent evidence, with SQL
              guardrails and a read-only application role.
            </motion.p>

            {/* CTA Group */}
            <motion.div
              className="cta-group"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1 }}
            >
              <a
                href="/chat"
                className="btn btn-primary btn-lg"
              >
                Launch DataMind <ArrowRight size={18} />
              </a>
              <a
                href="#pipeline"
                className="btn btn-secondary btn-lg"
              >
                Explore Architecture
              </a>
            </motion.div>
          </motion.div>

          {/* Three Modern Feature Cards */}
          <motion.div
            id="features"
            className="features-grid"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.2 }}
          >
            <div className="feature-card-modern">
              <div className="feature-card-glow" />
              <div>
                <div className="feature-icon-badge">
                  <Database size={26} />
                </div>
                <h3>Schema-Scoped SQL Generation</h3>
                <p>
                  Gemma classifies query intent and synthesizes ANSI-compliant SQL
                  strictly confined to dataset YAML table definitions and join
                  relationships.
                </p>
              </div>
              <span className="feature-meta-tag">GEMMA 3 • SCHEMA-GROUNDED</span>
            </div>

            <div className="feature-card-modern">
              <div className="feature-card-glow" />
              <div>
                <div className="feature-icon-badge">
                  <ShieldCheck size={26} />
                </div>
                <h3>Zero-Trust AST Guardrails</h3>
                <p>
                  Every proposed SQL statement is validated by an automated SQL
                  Guard AST parser. All mutations, unconfigured tables, and
                  unauthorized joins are blocked before reaching Snowflake.
                </p>
              </div>
              <span className="feature-meta-tag">AST PARSER • DATAMIND_READER</span>
            </div>

            <div className="feature-card-modern">
              <div className="feature-card-glow" />
              <div>
                <div className="feature-icon-badge">
                  <Activity size={26} />
                </div>
                <h3>Verified Evidence & Query IDs</h3>
                <p>
                  Answers are accompanied by transparent evidence: the exact SQL
                  run, the verified Snowflake Query ID, execution latency, and
                  plain-English row explanations.
                </p>
              </div>
              <span className="feature-meta-tag">AUDIT TRAIL • QUERY EVIDENCE</span>
            </div>
          </motion.div>
        </div>
      </section>

      {/* --- Capabilities Bento Grid Section --- */}
      <section
        id="bento"
        style={{
          position: "relative",
          padding: "6rem 2rem",
          background:
            "linear-gradient(180deg, #090D0B 0%, #0D1410 40%, #090D0B 100%)",
          zIndex: 1,
          width: "100%",
          borderTop: "1px solid #1E2D24",
        }}
      >
        <div
          style={{
            maxWidth: "1200px",
            margin: "0 auto",
            textAlign: "center",
          }}
        >
          <div className="pipeline-pill" style={{ margin: "0 auto 1.5rem" }}>
            Capabilities & Architecture
          </div>
          <h2
            style={{
              fontSize: "clamp(2rem, 4vw, 2.75rem)",
              fontWeight: "700",
              marginBottom: "1rem",
              background: "linear-gradient(to right, #ECFDF5, #10B981)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              fontFamily: "var(--font-display)",
            }}
          >
            Engineered for Verifiable Analytics
          </h2>
          <p
            style={{
              color: "#9CA3AF",
              fontSize: "1.15rem",
              marginBottom: "4rem",
              maxWidth: "650px",
              marginLeft: "auto",
              marginRight: "auto",
              lineHeight: 1.6,
            }}
          >
            A cohesive stack linking lightweight language models with Snowflake's
            analytical compute under strict least-privilege security.
          </p>

          <MagicBento
            textAutoHide={true}
            enableSpotlight={true}
            enableBorderGlow={true}
            spotlightRadius={320}
            glowColor="16, 185, 129"
          />
        </div>
      </section>

      {/* --- Pipeline Steps Section --- */}
      <PipelineSteps />

      {/* --- Footer --- */}
      <footer className="landing-footer">
        <div className="footer-content">
          <div className="footer-col">
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                marginBottom: "1rem",
              }}
            >
              <div
                style={{
                  width: "32px",
                  height: "32px",
                  borderRadius: "8px",
                  backgroundColor: "rgba(16, 185, 129, 0.15)",
                  border: "1px solid rgba(16, 185, 129, 0.4)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#10B981",
                }}
              >
                <Database size={18} />
              </div>
              <h4 style={{ margin: 0, color: "#ECFDF5", fontSize: "1.25rem" }}>
                DataMind
              </h4>
            </div>
            <p>
              Natural-language question answering over Snowflake datasets with
              Gemma 3, AST guardrails, and read-only role isolation.
            </p>
          </div>

          <div className="footer-col">
            <h4>Architecture</h4>
            <a href="#pipeline">FastAPI Service</a>
            <a href="#pipeline">Gemma 3 (Ollama/Hosted)</a>
            <a href="#features">AST SQL Guard</a>
            <a href="#features">DATAMIND_READER Role</a>
          </div>

          <div className="footer-col">
            <h4>Datasets & Demos</h4>
            <a href="/chat">
              Bank Marketing Dataset
            </a>
            <a href="/chat">
              TPC-H Benchmark
            </a>
            <a href="/chat">
              Reversible Changes Demo
            </a>
            <a href="/chat">
              Health Monitor API
            </a>
          </div>

          <div className="footer-col">
            <h4>Repository</h4>
            <a
              href="https://github.com/nikunjsrivastav/Data-mind"
              target="_blank"
              rel="noreferrer"
            >
              GitHub Source <ExternalLink size={12} style={{ display: "inline" }} />
            </a>
            <a href="https://github.com/nikunjsrivastav/Data-mind/blob/main/docs/architecture.md" target="_blank" rel="noreferrer">
              Architecture Spec
            </a>
            <a href="https://github.com/nikunjsrivastav/Data-mind/blob/main/docs/api_contract.md" target="_blank" rel="noreferrer">
              API Contract
            </a>
            <a href="https://github.com/nikunjsrivastav/Data-mind/blob/main/LICENSE" target="_blank" rel="noreferrer">
              MIT License
            </a>
          </div>
        </div>

        <div className="footer-bottom">
          <p>&copy; {new Date().getFullYear()} DataMind Project. MIT Licensed.</p>
          <div style={{ display: "flex", gap: "1.5rem" }}>
            <span style={{ color: "#34D399", fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}>
              READ-ONLY QUERY ROLE
            </span>
          </div>
        </div>
      </footer>
    </main>
  );
}
