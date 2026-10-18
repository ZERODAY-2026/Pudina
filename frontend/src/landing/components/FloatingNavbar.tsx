"use client";
import { useState } from "react";
import { motion, useScroll, useMotionValueEvent } from "framer-motion";
import { Database, Sparkles, ExternalLink } from "lucide-react";

export default function FloatingNavbar() {
  const { scrollY } = useScroll();
  const [isScrolled, setIsScrolled] = useState(false);

  useMotionValueEvent(scrollY, "change", (latest) => {
    if (latest > 40) {
      setIsScrolled(true);
    } else {
      setIsScrolled(false);
    }
  });

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 100,
        display: "flex",
        justifyContent: "center",
        paddingTop: isScrolled ? "1rem" : "0",
        transition: "padding-top 0.3s cubic-bezier(0.16, 1, 0.3, 1)",
        pointerEvents: "none",
      }}
    >
      <motion.nav
        initial={{
          width: "100%",
          borderRadius: "0px",
          backgroundColor: "rgba(9, 13, 11, 0)",
          borderBottom: "1px solid rgba(30, 45, 36, 0.6)",
          y: 0,
        }}
        animate={{
          width: isScrolled ? "90%" : "100%",
          borderRadius: isScrolled ? "16px" : "0px",
          backgroundColor: isScrolled
            ? "rgba(15, 22, 18, 0.85)"
            : "rgba(9, 13, 11, 0.3)",
          backdropFilter: "blur(14px)",
          borderBottom: isScrolled
            ? "1px solid rgba(16, 185, 129, 0.3)"
            : "1px solid rgba(30, 45, 36, 0.5)",
          borderColor: isScrolled
            ? "rgba(16, 185, 129, 0.35)"
            : "rgba(30, 45, 36, 0.5)",
        }}
        transition={{ duration: 0.3, ease: "easeInOut" }}
        style={{
          height: "70px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 2rem",
          maxWidth: isScrolled ? "1200px" : "100%",
          gap: "2rem",
          pointerEvents: "auto",
          boxShadow: isScrolled ? "0 12px 35px -8px rgba(0, 0, 0, 0.7), 0 0 20px rgba(16, 185, 129, 0.12)" : "none",
          whiteSpace: "nowrap",
        }}
      >
        {/* Brand Area */}
        <a
          href="/"
          style={{ display: "flex", alignItems: "center", gap: "0.75rem", textDecoration: "none" }}
        >
          <div
            style={{
              width: "38px",
              height: "38px",
              borderRadius: "10px",
              backgroundColor: "rgba(16, 185, 129, 0.15)",
              border: "1px solid rgba(16, 185, 129, 0.4)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#10B981",
              boxShadow: "0 0 15px rgba(16, 185, 129, 0.25)",
            }}
          >
            <Database size={20} />
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span
              style={{
                color: "#ECFDF5",
                fontWeight: "700",
                fontSize: "1.15rem",
                letterSpacing: "-0.02em",
                fontFamily: "var(--font-display)",
              }}
            >
              DataMind
            </span>
            <span
              style={{
                color: "#10B981",
                fontSize: "0.6875rem",
                fontWeight: "600",
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                fontFamily: "var(--font-mono)",
              }}
            >
              Snowflake SQL AI
            </span>
          </div>
        </a>

        {/* Navigation Links */}
        <div
          style={{
            display: "flex",
            gap: "2rem",
            alignItems: "center",
          }}
        >
          <a
            href="#features"
            style={{
              color: "#D1D5DB",
              fontSize: "0.9375rem",
              fontWeight: "500",
              transition: "color 0.2s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#34D399")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#D1D5DB")}
          >
            Features
          </a>
          <a
            href="#pipeline"
            style={{
              color: "#D1D5DB",
              fontSize: "0.9375rem",
              fontWeight: "500",
              transition: "color 0.2s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#34D399")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#D1D5DB")}
          >
            Architecture
          </a>
          <a
            href="#bento"
            style={{
              color: "#D1D5DB",
              fontSize: "0.9375rem",
              fontWeight: "500",
              transition: "color 0.2s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#34D399")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#D1D5DB")}
          >
            Capabilities
          </a>
          <a
            href="https://github.com/nikunjsrivastav/Data-mind"
            target="_blank"
            rel="noreferrer"
            style={{
              color: "#9CA3AF",
              fontSize: "0.9375rem",
              fontWeight: "500",
              display: "inline-flex",
              alignItems: "center",
              gap: "0.3rem",
              transition: "color 0.2s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#ECFDF5")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#9CA3AF")}
          >
            Docs <ExternalLink size={14} />
          </a>
        </div>

        {/* CTA Button */}
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <a
            href="/chat"
            className="btn btn-primary"
            style={{
              padding: "0.55rem 1.35rem",
              fontSize: "0.9rem",
              borderRadius: "10px",
            }}
          >
            <Sparkles size={16} />
            Launch App
          </a>
        </div>
      </motion.nav>
    </div>
  );
}
