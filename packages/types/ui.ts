/**
 * UI Component Types
 * Obsidian Design System Components
 */

/**
 * State for voice activity and pulse animation
 */
export interface PulseState {
  /** Current volume level (0.0 - 1.0) */
  volume: number;
  /**
   * Sentiment score (0.0 - 1.0)
   * MVP: Always neutral (0.5), included for future compatibility
   * Post-MVP: Will drive color interpolation (Zinc → Blue → Emerald)
   */
  sentiment: number;
  /** Whether voice activity is currently detected */
  isActive: boolean;
  /** Timestamp of last interruption event, if any */
  lastInterruptionAt?: Date;
}

/**
 * Props for Pulse-Maker visual component
 */
export interface PulseMakerProps {
  /** Unique identifier for the agent/call */
  agentId: string;
  /** Current volume level (0.0 - 1.0), defaults to 0 */
  volume?: number;
  /**
   * Sentiment score (0.0 - 1.0), defaults to 0.5 (neutral)
   * MVP: Accepted but ignored for rendering (always uses blue color)
   * Post-MVP: Will drive color interpolation through Zinc → Blue → Emerald spectrum
   */
  sentiment?: number;
  /** Whether animations are enabled, defaults to true */
  motionEnabled?: boolean;
  /**
   * Callback when pulse state changes
   * Note: Sentiment is included in state for future compatibility,
   * but is not used for rendering in MVP
   */
  onStateChange?: (state: PulseState) => void;
}
