"use client";
import { motion } from "framer-motion";
import { MessageSquareText, Code2, ShieldCheck, Database, ArrowRight } from "lucide-react";
import "./PipelineSteps.css";

const steps = [
  {
    id: 1,
    step: "01 - INTENT & CLASSIFY",
    title: "Question Ingestion",
    description:
      "Users submit natural-language analytics questions. Gemma identifies user intent, filters, target entities, and maps them to the configured dataset catalog.",
    icon: MessageSquareText,
  },
  {
    id: 2,
    step: "02 - SCHEMA MAPPING",
    title: "Gemma 3 SQL Synthesis",
    description:
      "Gemma constructs ANSI-compliant SQL queries restricted exclusively to pre-configured tables, allowed column scopes, and verified join paths.",
    icon: Code2,
  },
  {
    id: 3,
    step: "03 - AST VALIDATION",
    title: "SQL Guard Verification",
    description:
      "An automated SQL guard parses the Abstract Syntax Tree before query transmission, verifying read-only safety and blocking any mutation or forbidden clauses.",
    icon: ShieldCheck,
  },
  {
    id: 4,
    step: "04 - EXECUTION & EVIDENCE",
    title: "Snowflake Lineage & Synthesis",
    description:
      "Snowflake executes the validated query via the DATAMIND_READER role. Gemma explains returned rows while streaming the official Query ID and evidence trail.",
    icon: Database,
  },
];

export default function PipelineSteps() {
  return (
    <section
      id="pipeline"
      className="pipeline-section"
      style={{
        background: "linear-gradient(180deg, #090D0B 0%, #0F1612 50%, #090D0B 100%)",
        position: "relative",
        borderTop: "1px solid #1E2D24",
      }}
    >
      <div className="pipeline-container">
        {/* Left: Sticky Overview */}
        <div className="pipeline-left">
          <div className="pipeline-pill">Architecture Pipeline</div>
          <h2 className="pipeline-heading">
            How DataMind Executes Queries
          </h2>
          <p className="pipeline-subheading">
            A secure four-stage pipeline bridging conversational LLMs with enterprise
            data warehouses under strict zero-trust principles.
          </p>
          <div style={{ marginTop: "2rem" }}>
            <a
              href="/chat"
              className="btn btn-secondary"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.5rem",
                padding: "0.75rem 1.75rem",
                borderRadius: "12px",
                fontSize: "0.95rem",
              }}
            >
              Test Live Query <ArrowRight size={16} />
            </a>
          </div>
        </div>

        {/* Right: Steps */}
        <div className="pipeline-right">
          {steps.map((s, idx) => {
            const Icon = s.icon;
            return (
              <motion.div
                key={s.id}
                className="pipeline-card"
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.5, delay: idx * 0.1 }}
              >
                <div className="card-visual" />
                <span className="card-step-number">{s.step}</span>
                <div className="card-step-badge">
                  <Icon size={22} />
                </div>
                <h3 className="card-title">{s.title}</h3>
                <p className="card-description">{s.description}</p>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
