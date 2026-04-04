"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface AdvancedVoiceConfigProps {
  onSave?: (config: AdvancedConfig) => Promise<void>;
  currentConfig?: AdvancedConfig;
  disabled?: boolean;
}

export interface AdvancedConfig {
  speech_speed: number;
  stability: number;
  temperature: number;
}

const DEFAULT_CONFIG: AdvancedConfig = {
  speech_speed: 1.0,
  stability: 0.8,
  temperature: 0.7,
};

export function AdvancedVoiceConfig({
  onSave,
  currentConfig = DEFAULT_CONFIG,
  disabled = false,
}: AdvancedVoiceConfigProps) {
  const [config, setConfig] = React.useState<AdvancedConfig>(currentConfig);
  const [saving, setSaving] = React.useState(false);
  const [saved, setSaved] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Update local config when currentConfig changes
  React.useEffect(() => {
    setConfig(currentConfig);
    setSaved(false);
    setError(null);
  }, [currentConfig]);

  const handleChange = (field: keyof AdvancedConfig, value: number) => {
    setConfig((prev) => ({ ...prev, [field]: value }));
    setSaved(false);
    setError(null);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);

    try {
      await onSave?.(config);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save configuration");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setConfig(DEFAULT_CONFIG);
    setSaved(false);
    setError(null);
  };

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h3 className="text-lg font-semibold text-foreground">
          Advanced Voice Configuration
        </h3>
        <p className="text-sm text-muted-foreground">
          Fine-tune voice parameters for custom behavior. Use with caution.
        </p>
      </div>

      {/* Warning Message */}
      <div className="rounded-lg border border-amber-500/50 bg-amber-500/10 p-4">
        <div className="flex items-start gap-3">
          <span className="text-amber-600 dark:text-amber-400 text-xl">⚠️</span>
          <div className="flex-1">
            <p className="text-sm font-medium text-amber-600 dark:text-amber-400">
              Advanced Settings Warning
            </p>
            <p className="text-sm text-amber-600/80 dark:text-amber-400/80 mt-1">
              Custom settings may not sound optimal for your use case. Presets are
              tuned by experts for each scenario. Only adjust these if you have
              specific requirements.
            </p>
          </div>
        </div>
      </div>

      {/* Speech Speed Slider */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-foreground">
            Speech Speed
          </label>
          <span className="text-sm font-mono text-muted-foreground">
            {config.speech_speed.toFixed(2)}x
          </span>
        </div>
        <input
          type="range"
          min={0.5}
          max={2.0}
          step={0.05}
          value={config.speech_speed}
          onChange={(e) => handleChange("speech_speed", parseFloat(e.target.value))}
          disabled={disabled || saving}
          className={cn(
            "w-full h-2 bg-input rounded-lg appearance-none cursor-pointer",
            "accent-emerald-500",
            "[&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4",
            "[&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full",
            "[&::-webkit-slider-thumb]:bg-emerald-500",
            "[&::-webkit-slider-thumb]:cursor-pointer",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        />
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>0.5x (Slow)</span>
          <span>1.0x (Normal)</span>
          <span>2.0x (Fast)</span>
        </div>
      </div>

      {/* Stability Slider */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-foreground">
            Stability
          </label>
          <span className="text-sm font-mono text-muted-foreground">
            {config.stability.toFixed(2)}
          </span>
        </div>
        <input
          type="range"
          min={0.0}
          max={1.0}
          step={0.05}
          value={config.stability}
          onChange={(e) => handleChange("stability", parseFloat(e.target.value))}
          disabled={disabled || saving}
          className={cn(
            "w-full h-2 bg-input rounded-lg appearance-none cursor-pointer",
            "accent-emerald-500",
            "[&::-webkit-slider-thumb]:appearance-none [&&::-webkit-slider-thumb]:w-4",
            "[&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full",
            "[&::-webkit-slider-thumb]:bg-emerald-500",
            "[&::-webkit-slider-thumb]:cursor-pointer",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        />
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>0.0 (Variable)</span>
          <span>0.8 (Optimal)</span>
          <span>1.0 (Consistent)</span>
        </div>
      </div>

      {/* Temperature Slider */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-foreground">
            Temperature (Expressiveness)
          </label>
          <span className="text-sm font-mono text-muted-foreground">
            {config.temperature.toFixed(2)}
          </span>
        </div>
        <input
          type="range"
          min={0.0}
          max={1.0}
          step={0.05}
          value={config.temperature}
          onChange={(e) => handleChange("temperature", parseFloat(e.target.value))}
          disabled={disabled || saving}
          className={cn(
            "w-full h-2 bg-input rounded-lg appearance-none cursor-pointer",
            "accent-emerald-500",
            "[&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4",
            "[&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full",
            "[&::-webkit-slider-thumb]:bg-emerald-500",
            "[&::-webkit-slider-thumb]:cursor-pointer",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        />
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>0.0 (Flat)</span>
          <span>0.7 (Balanced)</span>
          <span>1.0 (Expressive)</span>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="rounded-lg border border-red-500/50 bg-red-500/10 p-4">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}

      {/* Success Display */}
      {saved && (
        <div className="rounded-lg border border-emerald-500/50 bg-emerald-500/10 p-4">
          <p className="text-sm text-emerald-600 dark:text-emerald-400">
            ✓ Custom voice configuration saved successfully
          </p>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          type="button"
          onClick={handleSave}
          disabled={disabled || saving}
          className={cn(
            "flex flex-1 items-center justify-center rounded-md px-4 py-2",
            "text-sm font-medium transition-colors",
            "bg-emerald-500 text-white hover:bg-emerald-600",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        >
          {saving ? "Saving..." : saved ? "Saved!" : "Save Configuration"}
        </button>

        <button
          type="button"
          onClick={handleReset}
          disabled={disabled || saving}
          className={cn(
            "flex flex-1 items-center justify-center rounded-md px-4 py-2",
            "text-sm font-medium transition-colors",
            "border border-input bg-card hover:bg-muted",
            "text-foreground",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        >
          Reset to Defaults
        </button>
      </div>

      {/* Value Guide */}
      <div className="rounded-lg border bg-muted/50 p-4 space-y-2">
        <p className="text-sm font-medium text-foreground">Value Guide</p>
        <div className="grid grid-cols-1 gap-2 text-xs text-muted-foreground">
          <div>
            <span className="font-medium">Speech Speed:</span> Controls how fast
            the voice speaks. 1.0x is normal speed.
          </div>
          <div>
            <span className="font-medium">Stability:</span> Controls voice
            consistency. Higher values (0.8-1.0) are more stable but less expressive.
          </div>
          <div>
            <span className="font-medium">Temperature:</span> Controls voice
            expressiveness. Lower values are more monotone, higher values are more emotional.
          </div>
        </div>
      </div>
    </div>
  );
}
