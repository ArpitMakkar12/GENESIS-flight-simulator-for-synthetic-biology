"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import Link from "next/link";
import { GENESIS_STATS } from "@/lib/presets";

/* ─── Particle type ───────────────────────────────────────── */
interface Particle {
  x: number;
  y: number;
  r: number;
  a: number;
}

/* ─── Constants ───────────────────────────────────────────── */
const PARTICLE_COUNT = 80;
const IDLE_HEAT = 0.4;
const IDLE_HUE = 170;
const DPR_CAP = 2;

/* ─── Component ───────────────────────────────────────────── */

export default function MicroscopeHero({
  apiStatus,
}: {
  apiStatus: "checking" | "online" | "offline";
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number>(0);
  const particlesRef = useRef<Particle[]>([]);
  const lastTimeRef = useRef<number>(0);
  const isVisibleRef = useRef(true);
  const isInViewRef = useRef(true);
  const isReducedMotionRef = useRef(false);
  const hasDrawnStaticRef = useRef(false);
  const [reducedMotion, setReducedMotion] = useState(false);

  /* ── Draw one frame of particles ── */
  const drawParticles = useCallback(
    (ctx: CanvasRenderingContext2D, w: number, h: number, dt: number) => {
      ctx.clearRect(0, 0, w, h);
      ctx.globalCompositeOperation = "lighter";
      const speed = (0.15 + IDLE_HEAT * 1.6) * 0.85;

      particlesRef.current.forEach((p) => {
        if (dt > 0) {
          p.a += (Math.random() - 0.5) * 0.8;
          p.x = (p.x + Math.cos(p.a) * dt * 0.08 * speed + 1) % 1;
          p.y = (p.y + Math.sin(p.a) * dt * 0.08 * speed + 1) % 1;
        }
        const X = p.x * w;
        const Y = p.y * h;
        const R = p.r * (1 + IDLE_HEAT * 0.6);

        // Soft outer glow
        ctx.fillStyle = `hsla(${IDLE_HUE},100%,65%,0.10)`;
        ctx.beginPath();
        ctx.arc(X, Y, R * 4, 0, Math.PI * 2);
        ctx.fill();

        // Bright core
        ctx.fillStyle = `hsla(${IDLE_HUE},100%,75%,0.75)`;
        ctx.beginPath();
        ctx.arc(X, Y, R, 0, Math.PI * 2);
        ctx.fill();
      });
    },
    []
  );

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    /* ── Init particles ── */
    particlesRef.current = Array.from({ length: PARTICLE_COUNT }, () => ({
      x: Math.random(),
      y: Math.random(),
      r: 0.6 + Math.random() * 1.8,
      a: Math.random() * Math.PI * 2,
    }));
    hasDrawnStaticRef.current = false;

    /* ── Resize handler ── */
    const fit = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(DPR_CAP, window.devicePixelRatio || 1);
      canvas.width = Math.max(1, rect.width * dpr);
      canvas.height = Math.max(1, rect.height * dpr);
      // Redraw immediately on resize so the canvas isn't blank
      if (isReducedMotionRef.current) {
        drawParticles(ctx, canvas.width, canvas.height, 0);
      }
    };
    const resizeObs = new ResizeObserver(fit);
    resizeObs.observe(canvas);
    fit();

    /* ── IntersectionObserver — pause when off-screen ── */
    const intObs = new IntersectionObserver(
      (entries) => {
        isInViewRef.current = entries[0].isIntersecting;
      },
      { threshold: 0.05 }
    );
    intObs.observe(canvas);

    /* ── Visibility change — pause when tab hidden ── */
    const onVisChange = () => {
      isVisibleRef.current = !document.hidden;
    };
    document.addEventListener("visibilitychange", onVisChange);

    /* ── Reduced motion — react to live changes ── */
    const rmQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onRmChange = () => {
      isReducedMotionRef.current = rmQuery.matches;
      setReducedMotion(rmQuery.matches);
      if (rmQuery.matches) {
        // Draw one static frame when switching to reduced motion
        hasDrawnStaticRef.current = false;
      }
    };
    onRmChange();
    rmQuery.addEventListener("change", onRmChange);

    /* ── Draw initial static frame if starting with reduced motion ── */
    if (isReducedMotionRef.current) {
      drawParticles(ctx, canvas.width, canvas.height, 0);
      hasDrawnStaticRef.current = true;
    }

    /* ── Animation loop (always runs; checks refs to decide what to do) ── */
    lastTimeRef.current = performance.now();

    const frame = (time: number) => {
      const dt = Math.min(0.05, (time - lastTimeRef.current) / 1000);
      lastTimeRef.current = time;

      if (isReducedMotionRef.current) {
        // In reduced-motion mode: draw one static frame, then idle
        if (!hasDrawnStaticRef.current) {
          drawParticles(ctx, canvas.width, canvas.height, 0);
          hasDrawnStaticRef.current = true;
        }
      } else if (isVisibleRef.current && isInViewRef.current) {
        // Normal mode: animate
        hasDrawnStaticRef.current = false;
        drawParticles(ctx, canvas.width, canvas.height, dt);
      }

      rafRef.current = requestAnimationFrame(frame);
    };
    rafRef.current = requestAnimationFrame(frame);

    /* ── Cleanup — safe under Strict Mode double-invoke ── */
    return () => {
      cancelAnimationFrame(rafRef.current);
      resizeObs.disconnect();
      intObs.disconnect();
      document.removeEventListener("visibilitychange", onVisChange);
      rmQuery.removeEventListener("change", onRmChange);
    };
  }, [drawParticles]);

  return (
    <div className="relative w-full min-h-[420px] sm:min-h-[480px] rounded-2xl overflow-hidden mb-12">
      {/* ── Radial gradient background (matches Direction C) ── */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse at 60% 45%, #06364a 0%, #031722 45%, #01070c 100%)",
        }}
      />

      {/* ── Canvas particle field ── */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none"
        aria-hidden="true"
      />

      {/* ── SVG Cell — anchored right on md+, behind text on mobile ── */}
      <div className="absolute inset-0 flex items-center pointer-events-none
                      justify-center md:justify-end md:pr-[6%]
                      opacity-30 md:opacity-100">
        <svg
          className={`w-[260px] sm:w-[300px] md:w-[380px] lg:w-[430px] h-auto overflow-visible ${reducedMotion ? "" : "animate-cell-jitter"}`}
          viewBox="-24 -6 344 142"
          aria-hidden="true"
          style={{
            filter: `drop-shadow(0 0 14px hsla(${IDLE_HUE}, 100%, 55%, 0.7))`,
          }}
        >
          {/* Flagellum */}
          <g
            className={reducedMotion ? "" : "animate-cell-wave"}
            style={{
              transformBox: "fill-box" as const,
              transformOrigin: "right center",
            }}
          >
            <path
              d="M31 62 C16 40 6 84 -8 58 S-20 72 -24 64"
              fill="none"
              stroke={`hsla(${IDLE_HUE}, 100%, 70%, 0.7)`}
              strokeWidth="1.2"
            />
          </g>
          {/* Cell body */}
          <g
            className={reducedMotion ? "" : "animate-cell-breathe"}
            style={{
              transformBox: "fill-box" as const,
              transformOrigin: "center",
            }}
          >
            <rect x="30" y="32" width="252" height="64" rx="32"
              fill={`hsla(${IDLE_HUE}, 100%, 60%, 0.08)`}
              stroke={`hsl(${IDLE_HUE}, 100%, 65%)`}
              strokeWidth="1.6" />
            <rect x="37" y="39" width="238" height="50" rx="25"
              fill="none"
              stroke={`hsla(${IDLE_HUE}, 100%, 65%, 0.4)`}
              strokeWidth="1" />
            <path d="M72 64 C92 44 112 84 132 64 S172 44 192 64 S232 84 252 64"
              fill="none"
              stroke={`hsl(${IDLE_HUE}, 100%, 78%)`}
              strokeWidth="1.5" />
            <g fill={`hsl(${IDLE_HUE}, 100%, 82%)`}>
              <circle cx="60" cy="52" r="2.2" />
              <circle cx="84" cy="80" r="2.2" />
              <circle cx="148" cy="48" r="2.2" />
              <circle cx="170" cy="80" r="2.2" />
              <circle cx="214" cy="50" r="2.2" />
              <circle cx="240" cy="78" r="2.2" />
              <circle cx="120" cy="84" r="2.2" />
              <circle cx="198" cy="82" r="2.2" />
            </g>
          </g>
        </svg>
      </div>

      {/* ── Scale bar (bottom-right, microscope feel) ── */}
      <div className="absolute right-4 bottom-[100px] sm:bottom-[110px] z-10 hidden md:flex items-center gap-1.5 text-[10px] text-[#8cc3d4] pointer-events-none">
        <span className="block w-[44px] h-[2px] bg-[#8cc3d4]" />
        2 µm
      </div>

      {/* ── Text scrim — covers left ~60% for contrast ── */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "linear-gradient(to right, rgba(1,7,12,0.92) 0%, rgba(1,7,12,0.75) 35%, rgba(1,7,12,0.3) 55%, transparent 70%)",
        }}
      />

      {/* ── Headline + CTAs (capped to ~55% on md+) ── */}
      <div className="relative z-10 flex flex-col justify-center h-full min-h-[420px] sm:min-h-[480px] px-6 sm:px-10 py-10">
        <div className="md:max-w-[55%]">
          <div className="flex items-center gap-2.5 mb-4">
            <div
              className={`h-2 w-2 rounded-full ${
                apiStatus === "online"
                  ? "bg-[#3ef2ff] shadow-[0_0_8px_rgba(62,242,255,0.6)]"
                  : apiStatus === "offline"
                    ? "bg-[#ff5a36]"
                    : "bg-[#ffcf66] pulse-glow"
              }`}
            />
            <span className="text-[11px] font-medium text-[#5c8494] uppercase tracking-widest">
              {apiStatus === "checking"
                ? "Connecting..."
                : apiStatus === "online"
                  ? "Engine Online"
                  : "Engine Offline"}
            </span>
          </div>

          <h1 className="text-4xl sm:text-5xl font-semibold text-[#eaffff] tracking-tight mb-4 glow-text leading-[1.1]">
            A flight simulator
            <br />
            <span className="text-[#3ef2ff]">for synthetic biology.</span>
          </h1>

          <p className="text-[#8cc3d4] leading-relaxed text-[15px] mb-6">
            Design genetic constructs. Set environmental conditions. Watch how{" "}
            <span className="text-[#7dffef] font-medium">E. coli K-12</span>{" "}
            responds — growth rate, metabolic flux, gene expression — computed
            from a genome-scale model with {GENESIS_STATS.reactions.value}{" "}
            reactions, in under 2 seconds.
          </p>

          <div className="flex flex-wrap gap-3">
            <Link
              href="/simulate"
              className="inline-flex px-6 py-2.5 rounded-full bg-[#3ef2ff]/15 text-[#7dffef] border border-[#3ef2ff]/40 text-sm font-semibold hover:bg-[#3ef2ff]/25 transition-all shadow-[0_0_24px_-6px_rgba(62,242,255,0.5)] hover:shadow-[0_0_32px_-6px_rgba(62,242,255,0.7)]"
            >
              ▶ Launch Simulation
            </Link>
            <Link
              href="/results"
              className="inline-flex px-6 py-2.5 rounded-full bg-white/[0.04] text-[#8cc3d4] border border-white/10 text-sm font-medium hover:bg-white/[0.07] hover:text-[#d9f7ff] transition-all"
            >
              View Past Results →
            </Link>
          </div>
        </div>

        {/* ── Glass stat chips (aligned with headline left edge) ── */}
        <div className="hidden sm:flex gap-2 mt-6 pointer-events-none">
          <div className="px-3 py-2 rounded-[10px] bg-white/[0.06] border border-white/[0.12] backdrop-blur-[10px] text-[11px] text-[#8cc3d4]">
            <span className="block text-[15px] font-semibold text-white">
              {GENESIS_STATS.reactions.value}
            </span>
            reactions
          </div>
          <div className="px-3 py-2 rounded-[10px] bg-white/[0.06] border border-white/[0.12] backdrop-blur-[10px] text-[11px] text-[#8cc3d4]">
            <span className="block text-[15px] font-semibold text-white">
              {GENESIS_STATS.genes.value}
            </span>
            genes
          </div>
        </div>
      </div>
    </div>
  );
}

