"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import {
  getVoicePresets,
  selectVoicePreset,
  getPresetSample,
  saveAdvancedVoiceConfig,
  getVoicePresetRecommendation,
  type VoicePresetRecommendation,
} from "@/actions/voice-presets";
import { AdvancedVoiceConfig } from "./AdvancedVoiceConfig";
import { RecommendationBanner } from "./RecommendationBanner";
import type { VoicePreset } from "@/actions/voice-presets";

interface VoicePresetSelectorProps {
  onComplete?: () => void;
}

type UseCase = "sales" | "support" | "marketing";

const USE_CASES: Array<{
  id: UseCase;
  name: string;
  description: string;
}> = [
  { id: "sales", name: "Sales", description: "High energy, confident tones" },
  { id: "support", name: "Support", description: "Calm, empathetic tones" },
  { id: "marketing", name: "Marketing", description: "Engaging, enthusiastic tones" },
];

export function VoicePresetSelector({ onComplete }: VoicePresetSelectorProps) {
  const [selectedUseCase, setSelectedUseCase] = React.useState<UseCase>("sales");
  const [presets, setPresets] = React.useState<VoicePreset[]>([]);
  const [selectedPresetId, setSelectedPresetId] = React.useState<number | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [selectingPresetId, setSelectingPresetId] = React.useState<number | null>(null); // Per-preset selecting state
  const [playingId, setPlayingId] = React.useState<number | null>(null);
  const [advancedMode, setAdvancedMode] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [successMessage, setSuccessMessage] = React.useState<string | null>(null);
  const [recommendation, setRecommendation] = React.useState<VoicePresetRecommendation | null>(null);
  const [recommendationDismissed, setRecommendationDismissed] = React.useState(false);

  // Web Audio API context
  const audioContextRef = React.useRef<AudioContext | null>(null);
  const currentSourceRef = React.useRef<AudioBufferSourceNode | null>(null);
  const audioBufferRef = React.useRef<AudioBuffer | null>(null);

  // Cleanup audio resources on unmount
  React.useEffect(() => {
    return () => {
      // Stop any playing audio
      if (currentSourceRef.current) {
        try {
          currentSourceRef.current.stop();
        } catch (e) {
          // Source may already be stopped
        }
        currentSourceRef.current = null;
      }

      // Close AudioContext
      if (audioContextRef.current && audioContextRef.current.state !== "closed") {
        audioContextRef.current.close().catch(console.error);
        audioContextRef.current = null;
      }
    };
  }, []);

  React.useEffect(() => {
    loadPresets();
    loadRecommendation();
  }, [selectedUseCase]);

  async function loadRecommendation() {
    try {
      const result = await getVoicePresetRecommendation(selectedUseCase);
      if (result.data && !result.error) {
        setRecommendation(result.data);
        setRecommendationDismissed(false);
      }
    } catch (err) {
      // Silently fail - recommendations are optional
      console.error("Failed to load recommendation:", err);
    }
  }

  async function loadPresets() {
    setLoading(true);
    setError(null);
    const result = await getVoicePresets(selectedUseCase);
    if (result.error) {
      setError(result.error);
    } else if (result.data) {
      setPresets(result.data);
    }
    setLoading(false);
  }

  async function handleSelectPreset(presetId: number) {
    setSelectingPresetId(presetId); // Use per-preset selecting state
    setError(null);
    setSuccessMessage(null);

    const result = await selectVoicePreset(presetId);
    if (result.error) {
      setError(result.error);
    } else {
      setSelectedPresetId(presetId);
      setSuccessMessage(result.data?.message || "Preset selected successfully");

      // Clear recommendation if we selected the recommended preset
      if (recommendation && recommendation.preset_id === presetId) {
        setRecommendation(null);
        setRecommendationDismissed(true);
      }

      setTimeout(() => {
        onComplete?.();
      }, 1500);
    }
    setSelectingPresetId(null);
  }

  async function handleApplyRecommendation() {
    if (!recommendation) return;
    await handleSelectPreset(recommendation.preset_id);
  }

  function handleDismissRecommendation() {
    setRecommendationDismissed(true);
  }

  async function handleSaveAdvancedConfig(config: {
    speech_speed: number;
    stability: number;
    temperature: number;
  }) {
    const result = await saveAdvancedVoiceConfig(config);
    if (result.error) {
      setError(result.error);
    } else {
      setSuccessMessage(result.data?.message || "Custom configuration saved successfully");
      setTimeout(() => {
        onComplete?.();
      }, 1500);
    }
  }

  async function handlePlaySample(presetId: number, e: React.MouseEvent) {
    e.stopPropagation();

    // Stop currently playing audio if any
    if (currentSourceRef.current) {
      try {
        currentSourceRef.current.stop();
      } catch (err) {
        // Source may already be stopped
      }
      currentSourceRef.current = null;
    }

    // If clicking the same playing preset, just stop and return
    if (playingId === presetId) {
      setPlayingId(null);
      return;
    }

    setPlayingId(presetId);
    const result = await getPresetSample(presetId);

    if (result.error || !result.data) {
      setError(result.error || "Failed to play sample");
      setPlayingId(null);
      return;
    }

    try {
      // Initialize AudioContext if needed
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
      }

      const audioContext = audioContextRef.current;

      // Resume AudioContext if suspended (required by browser autoplay policy)
      if (audioContext.state === "suspended") {
        await audioContext.resume();
      }

      // Decode audio data using Web Audio API
      const arrayBuffer = await result.data.arrayBuffer();
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
      audioBufferRef.current = audioBuffer;

      // Create and configure audio source
      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContext.destination);

      // Handle playback end
      source.onended = () => {
        setPlayingId(null);
        currentSourceRef.current = null;
      };

      // Handle playback errors
      source.onerror = (err) => {
        console.error("Audio playback error:", err);
        setError("Failed to play audio");
        setPlayingId(null);
        currentSourceRef.current = null;
      };

      // Start playback
      source.start(0);
      currentSourceRef.current = source;

    } catch (err: any) {
      console.error("Failed to play audio with Web Audio API:", err);
      setError(`Failed to play audio: ${err?.message || "Unknown error"}`);
      setPlayingId(null);
      currentSourceRef.current = null;
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h2 className="text-xl font-semibold text-foreground">
          Choose a voice preset
        </h2>
        <p className="text-sm text-muted-foreground">
          Select your use case and pick a voice preset optimized for it.
        </p>
      </div>

      {/* Recommendation Banner */}
      {recommendation && !recommendationDismissed && !advancedMode && (
        <RecommendationBanner
          presetName={recommendation.preset_name}
          improvementPct={recommendation.improvement_pct}
          reasoning={recommendation.reasoning}
          onApply={handleApplyRecommendation}
          onDismiss={handleDismissRecommendation}
        />
      )}

      {/* Use Case Selector */}
      <div className="flex gap-2">
        {USE_CASES.map((uc) => (
          <button
            key={uc.id}
            type="button"
            onClick={() => setSelectedUseCase(uc.id)}
            disabled={advancedMode}
            className={cn(
              "rounded-lg border px-4 py-2 text-sm font-medium transition-colors",
              "hover:border-emerald-500/50 hover:bg-muted/50",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              selectedUseCase === uc.id
                ? "border-emerald-500 bg-emerald-500/10 text-foreground"
                : "border-border bg-card text-muted-foreground"
            )}
          >
            {uc.name}
          </button>
        ))}
      </div>

      {/* Advanced Mode Toggle */}
      <div className="flex items-center justify-between rounded-lg border bg-card p-4">
        <div className="space-y-1">
          <div className="font-medium text-foreground">Advanced Mode</div>
          <div className="text-sm text-muted-foreground">
            Manually configure voice settings
          </div>
        </div>
        <button
          data-testid="advanced-mode-toggle"
          type="button"
          onClick={() => setAdvancedMode(!advancedMode)}
          className={cn(
            "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
            advancedMode ? "bg-emerald-500" : "bg-input"
          )}
        >
          <span
            className={cn(
              "inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
              advancedMode ? "translate-x-6" : "translate-x-1"
            )}
          />
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="rounded-lg border border-red-500/50 bg-red-500/10 p-4">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}

      {/* Success Display */}
      {successMessage && (
        <div className="rounded-lg border border-emerald-500/50 bg-emerald-500/10 p-4">
          <p className="text-sm text-emerald-600 dark:text-emerald-400">
            {successMessage}
          </p>
        </div>
      )}

      {/* Advanced Mode Component */}
      {advancedMode ? (
        <AdvancedVoiceConfig onSave={handleSaveAdvancedConfig} />
      ) : (
        <>
          {/* Preset Cards */}
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-muted-foreground">Loading presets...</div>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {presets.map((preset) => (
                <div
                  key={preset.id}
                  data-testid="preset-card"
                  data-preset-id={preset.id}
                  className={cn(
                    "relative rounded-lg border p-4 transition-all",
                    "hover:border-emerald-500/50 hover:shadow-md",
                    selectedPresetId === preset.id
                      ? "border-emerald-500 bg-emerald-500/10"
                      : "border-border bg-card"
                  )}
                >
                  {selectedPresetId === preset.id && (
                    <div
                      data-testid="preset-checkmark"
                      className="absolute right-2 top-2 flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500 text-white"
                    >
                      ✓
                    </div>
                  )}

                  <div className="space-y-2">
                    <h3 data-testid="preset-name" className="font-medium text-foreground">{preset.name}</h3>
                    <p className="text-sm text-muted-foreground">{preset.description}</p>

                    <div className="flex gap-2 pt-2">
                      <button
                        data-testid="play-sample-button"
                        type="button"
                        onClick={(e) => handlePlaySample(preset.id, e)}
                        disabled={playingId !== null && playingId !== preset.id}
                        aria-label={playingId === preset.id ? "Stop sample" : "Play sample"}
                        className={cn(
                          "flex flex-1 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                          "hover:bg-muted",
                          playingId === preset.id
                            ? "bg-emerald-500 text-white hover:bg-emerald-600"
                            : "bg-input text-foreground"
                        )}
                      >
                        {playingId === preset.id ? "⏸ Stop" : "▶ Play Sample"}
                      </button>

                      <button
                        data-testid="select-button"
                        type="button"
                        onClick={() => handleSelectPreset(preset.id)}
                        disabled={selectingPresetId !== null}
                        className={cn(
                          "flex flex-1 items-center justify-center rounded-md px-3 py-2 text-sm font-medium transition-colors",
                          "bg-emerald-500 text-white hover:bg-emerald-600",
                          "disabled:opacity-50 disabled:cursor-not-allowed"
                        )}
                      >
                        {selectingPresetId === preset.id ? "Saving..." : "Select"}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
