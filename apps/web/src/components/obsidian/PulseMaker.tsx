"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { useTranscriptStream } from "@/hooks/useTranscriptStream";
import { useVoiceEvents } from "@/hooks/useVoiceEvents";
import type { PulseMakerProps } from "@call/types";
import {
  PULSE_SCALE_MIN,
  PULSE_SCALE_MAX,
  PULSE_DURATION_MIN_MS,
  PULSE_DURATION_MAX_MS,
  PULSE_COLOR_DEFAULT,
  VOLUME_IDLE,
  VOLUME_SPEAKING,
  VOLUME_THRESHOLD,
  RIPPLE_DURATION_MS,
  RIPPLE_DELAY_1_MS,
  RIPPLE_DELAY_2_MS,
  RIPPLE_SIZE_1_PX,
  RIPPLE_SIZE_2_PX,
  RIPPLE_SIZE_3_PX,
  RIPPLE_SPACING_PX,
} from "@call/constants";
import "./PulseMaker.css";

/**
 * Pulse-Maker Visual Visualizer Component
 *
 * Displays a rhythmic "heartbeat" pulse for active calls in the Fleet Navigator.
 * Uses CSS animations for 60fps performance with no JavaScript overhead.
 *
 * MVP Scope:
 * - Binary volume state (speaking: 0.8, idle: 0.0)
 * - Neutral color (Electric Blue #3B82F6)
 * - Interruption ripple effect (Crimson #F43F5E)
 * - Motion reduction support (WCAG AAA)
 *
 * Post-MVP Enhancements:
 * - Continuous volume interpolation (requires Vapi amplitude data)
 * - Sentiment-based color transitions (requires sentiment analysis)
 */
export function PulseMaker({
  agentId,
  volume: propVolume,
  sentiment = 0.5,
  motionEnabled: propMotionEnabled = true,
  onStateChange,
}: PulseMakerProps) {
  // TODO: Extract callId from agent context or pass as prop
  // For now, use voiceEvents from useTranscriptStream
  const { voiceEvents } = useTranscriptStream(null);

  // Get voice events from transcript stream
  const { volume: voiceVolume, isActive, lastInterruptionAt } = useVoiceEvents(voiceEvents);

  // Use prop volume if provided, otherwise use voice events
  const volume = propVolume ?? voiceVolume;

  // Motion reduction detection
  const [prefersReducedMotion, setPrefersReducedMotion] = React.useState(false);

  React.useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReducedMotion(mediaQuery.matches);

    const handleChange = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches);
    };

    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  // Motion is enabled only if both prop and system preference allow
  const motionEnabled = propMotionEnabled && !prefersReducedMotion;

  // Binary volume state mapping (MVP)
  // volume >= VOLUME_THRESHOLD (0.8): speaking (scale 1.3, duration 0.5s)
  // volume < VOLUME_THRESHOLD (0.8): idle (scale 1.0, duration 2s)
  const isSpeaking = volume >= VOLUME_THRESHOLD;
  const pulseScale = isSpeaking ? PULSE_SCALE_MAX : PULSE_SCALE_MIN;
  const pulseDuration = isSpeaking
    ? `${PULSE_DURATION_MIN_MS}ms`
    : `${PULSE_DURATION_MAX_MS}ms`;

  // MVP: Always use neutral blue color (ignore sentiment prop)
  // Post-MVP: Implement color interpolation based on sentiment
  const pulseColor = PULSE_COLOR_DEFAULT;

  // Interruption ripple active state
  const [isInterruptionActive, setIsInterruptionActive] = React.useState(false);
  const rippleTimeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  React.useEffect(() => {
    if (lastInterruptionAt) {
      setIsInterruptionActive(true);

      // Reset ripple after animation duration - use constant
      if (rippleTimeoutRef.current) {
        clearTimeout(rippleTimeoutRef.current);
      }
      rippleTimeoutRef.current = setTimeout(() => {
        setIsInterruptionActive(false);
      }, RIPPLE_DURATION_MS);
    }

    return () => {
      if (rippleTimeoutRef.current) {
        clearTimeout(rippleTimeoutRef.current);
      }
    };
  }, [lastInterruptionAt, RIPPLE_DURATION_MS]);

  // Memoize state change callback to prevent infinite re-renders
  const pulseState = React.useMemo(() => ({
    volume,
    sentiment,
    isActive,
    lastInterruptionAt,
  }), [volume, sentiment, isActive, lastInterruptionAt]);

  // Notify parent of state changes with memoized callback
  React.useEffect(() => {
    onStateChange?.(pulseState);
  }, [pulseState, onStateChange]);

  // Status label for screen readers
  const statusLabel = React.useMemo(() => {
    if (lastInterruptionAt) return "interruption detected";
    if (isSpeaking) return "speaking";
    return "idle";
  }, [isSpeaking, lastInterruptionAt]);

  const volumePercent = Math.round(volume * 100);

  // Ripple ring sizes with consistent spacing
  const rippleSizes = React.useMemo(() => [
    RIPPLE_SIZE_1_PX, // Outer ripple (72px)
    RIPPLE_SIZE_2_PX, // Middle ripple (60px)
    RIPPLE_SIZE_3_PX, // Inner ripple (54px)
  ], []);

  const rippleDelays = React.useMemo(() => [
    0, // First ripple (no delay)
    RIPPLE_DELAY_1_MS, // Second ripple (50ms)
    RIPPLE_DELAY_2_MS, // Third ripple (100ms)
  ], []);

  return (
    <div
      data-pulse-maker="true"
      className="relative flex items-center justify-center"
      style={{
        width: "48px",
        height: "48px",
      }}
    >
      {/* Glassmorphism container with role="status" for screen readers */}
      <div
        role="status"
        aria-label={`Agent activity pulse, current state: ${statusLabel}`}
        className={cn(
          "relative flex items-center justify-center rounded-full",
          "bg-card/40 backdrop-blur-md",
          "border border-border",
          "shadow-[0_0_30px_rgba(0,0,0,0.3)]",
          "overflow-hidden"
        )}
        style={{
          width: "48px",
          height: "48px",
        }}
      >
        {/* Visually-hidden screen reader text - removed duplicate aria-live */}
        <span className="sr-only">
          Pulse: {statusLabel}, volume: {volumePercent}%
        </span>

        {/* CSS custom properties container */}
        <div
          className="pulse-maker"
          style={
            {
              "--pulse-scale": pulseScale,
              "--pulse-duration": pulseDuration,
              "--pulse-color": pulseColor,
            } as React.CSSProperties
          }
        >
          {/* Ripple rings (concentric) - animate continuously based on voice activity */}
          {rippleSizes.map((size, index) => (
            <div
              key={`ripple-${index}`}
              data-pulse-ripple="true"
              className={cn(
                "pulse-ripple absolute border-2",
                isInterruptionActive && "active interruption",
                isActive && "speaking" // Add continuous animation for voice activity
              )}
              style={{
                borderColor: isInterruptionActive ? "#f43f5e" : `var(--pulse-color)`,
                width: `${size}px`,
                height: `${size}px`,
                top: "50%",
                left: "50%",
                marginTop: `-${size / 2}px`,
                marginLeft: `-${size / 2}px`,
                animationDelay: `${rippleDelays[index]}ms`,
              }}
            />
          ))}

          {/* Core heartbeat circle */}
          <div
            data-pulse-core="true"
            className={cn(
              "pulse-core rounded-full shadow-lg",
              !motionEnabled && "static"
            )}
            style={{
              width: "32px",
              height: "32px",
              backgroundColor: `var(--pulse-color)`,
              boxShadow: `0 0 20px var(--pulse-color)`,
            }}
          />
        </div>
      </div>
    </div>
  );
}
