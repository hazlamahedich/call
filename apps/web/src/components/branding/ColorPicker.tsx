"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const HEX_RE = /^#[0-9a-fA-F]{6}$/;
const DEBOUNCE_MS = 300;

interface ColorPickerProps {
  value: string;
  onChange: (hex: string) => void;
}

export function ColorPicker({ value, onChange }: ColorPickerProps) {
  const [text, setText] = useState(value);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    setText(value);
  }, [value]);

  const debouncedOnChange = useCallback(
    (hex: string) => {
      clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => onChange(hex), DEBOUNCE_MS);
    },
    [onChange],
  );

  const handleTextChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setText(val);
    setError(null);
    if (HEX_RE.test(val)) {
      debouncedOnChange(val);
    } else if (val.length === 7) {
      setError("Invalid hex color");
    }
  };

  const handleSwatchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setText(val);
    setError(null);
    onChange(val);
  };

  return (
    <div className="flex flex-col gap-xs">
      <div className="flex items-center gap-sm">
        <input
          type="color"
          value={HEX_RE.test(text) ? text : "#10B981"}
          onChange={handleSwatchChange}
          aria-label="Color swatch"
          className="size-10 cursor-pointer rounded border border-border bg-transparent"
        />
        <Input
          type="text"
          value={text}
          onChange={handleTextChange}
          placeholder="#10B981"
          maxLength={7}
          error={!!error}
          className="w-32"
        />
      </div>
      <div
        className={cn(
          "h-6 rounded border border-border",
          !error && HEX_RE.test(text) && "shadow-[0_0_8px_rgba(0,0,0,0.3)]",
        )}
        style={{ backgroundColor: HEX_RE.test(text) ? text : "#10B981" }}
      />
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
