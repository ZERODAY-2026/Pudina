"use client";
import { useRef, useEffect, useCallback, useState } from "react";
import { gsap } from "gsap";
import {
  Database,
  ShieldCheck,
  Bot,
  Terminal,
  Activity,
  FileCode,
  Layers,
} from "lucide-react";
import "./MagicBento.css";

const DEFAULT_SPOTLIGHT_RADIUS = 300;
const DEFAULT_GLOW_COLOR = "16, 185, 129";
const MOBILE_BREAKPOINT = 768;

const cardData = [
  {
    color: "#0F1612",
    title: "Snowflake Reader Role",
    description: "Queries use the DATAMIND_READER role, which is configured for read-only access.",
    label: "Security",
    icon: ShieldCheck,
  },
  {
    color: "#0F1612",
    title: "Gemma 3 Intelligence",
    description: "Local Ollama or hosted Gemma engine classifies queries and translates natural language to SQL.",
    label: "AI Engine",
    icon: Bot,
  },
  {
    color: "#0F1612",
    title: "AST SQL Guard",
    description: "Parses abstract syntax trees before execution to block unconfigured tables and mutation attempts.",
    label: "Guardrail",
    icon: Terminal,
  },
  {
    color: "#0F1612",
    title: "Verified Audit Evidence",
    description: "Every answer provides the live Snowflake Query ID, duration, and expandable raw query results.",
    label: "Auditability",
    icon: Activity,
  },
  {
    color: "#0F1612",
    title: "Enterprise Snowflake Intelligence",
    description:
      "A complete closed-loop architecture combining FastAPI, Gemma 3, and Snowflake with strict zero-trust guardrails. Ask questions naturally and receive verifiable tabular facts.",
    label: "Core Architecture",
    icon: Database,
  },
  {
    color: "#0F1612",
    title: "Declarative Dataset Scoping",
    description: "YAML-driven catalogs define tables, allowed joins, and semantic context for enterprise domains.",
    label: "Configuration",
    icon: Layers,
  },
  {
    color: "#0F1612",
    title: "Reversible Sandbox Demo",
    description: "Simulate and test data operations safely on isolated clones without modifying production source tables.",
    label: "Sandbox",
    icon: FileCode,
  },
];

interface MagicBentoProps {
  textAutoHide?: boolean;
  enableSpotlight?: boolean;
  enableBorderGlow?: boolean;
  spotlightRadius?: number;
  glowColor?: string;
}

export default function MagicBento({
  textAutoHide = true,
  enableSpotlight = true,
  enableBorderGlow = true,
  spotlightRadius = DEFAULT_SPOTLIGHT_RADIUS,
  glowColor = DEFAULT_GLOW_COLOR,
}: MagicBentoProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const spotlightRef = useRef<HTMLDivElement>(null);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      if (spotlightRef.current && enableSpotlight && !isMobile) {
        gsap.to(spotlightRef.current, {
          x,
          y,
          opacity: 0.8,
          duration: 0.2,
          ease: "power2.out",
        });
      }

      if (enableBorderGlow && !isMobile) {
        const cards = containerRef.current.querySelectorAll<HTMLElement>(
          ".magic-bento-card--border-glow"
        );
        cards.forEach((card) => {
          const cardRect = card.getBoundingClientRect();
          const cardX = e.clientX - cardRect.left;
          const cardY = e.clientY - cardRect.top;
          card.style.setProperty("--glow-x", `${cardX}px`);
          card.style.setProperty("--glow-y", `${cardY}px`);
          card.style.setProperty("--glow-intensity", "1");
        });
      }
    },
    [enableSpotlight, enableBorderGlow, isMobile]
  );

  const handleMouseLeave = useCallback(() => {
    if (spotlightRef.current) {
      gsap.to(spotlightRef.current, {
        opacity: 0,
        duration: 0.5,
      });
    }
    if (containerRef.current) {
      const cards = containerRef.current.querySelectorAll<HTMLElement>(
        ".magic-bento-card--border-glow"
      );
      cards.forEach((card) => {
        card.style.setProperty("--glow-intensity", "0");
      });
    }
  }, []);

  return (
    <div
      ref={containerRef}
      className="bento-section"
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{ position: "relative", width: "100%" }}
    >
      {enableSpotlight && !isMobile && (
        <div
          ref={spotlightRef}
          className="global-spotlight"
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: `${spotlightRadius * 2}px`,
            height: `${spotlightRadius * 2}px`,
            borderRadius: "50%",
            background: `radial-gradient(circle, rgba(${glowColor}, 0.15) 0%, rgba(${glowColor}, 0.05) 40%, transparent 70%)`,
            transform: "translate(-50%, -50%)",
            pointerEvents: "none",
            opacity: 0,
            zIndex: 10,
          }}
        />
      )}

      <div className="card-grid">
        {cardData.map((card, idx) => {
          const Icon = card.icon;
          return (
            <div
              key={idx}
              className={`magic-bento-card ${
                enableBorderGlow ? "magic-bento-card--border-glow" : ""
              } ${textAutoHide ? "magic-bento-card--text-autohide" : ""}`}
              style={{
                backgroundColor: card.color,
              }}
            >
              <div className="magic-bento-card__header">
                <div className="magic-bento-card__icon">
                  <Icon size={22} />
                </div>
                <span className="magic-bento-card__label">{card.label}</span>
              </div>
              <div className="magic-bento-card__content">
                <h3 className="magic-bento-card__title">{card.title}</h3>
                <p className="magic-bento-card__description">
                  {card.description}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
