"use client";

import { useState, useRef, useEffect, KeyboardEvent } from "react";
import type { SourceAttribution } from "@/actions/scripts-lab";

interface SourceTooltipProps {
  sources: SourceAttribution[];
}

export function SourceTooltip({ sources }: SourceTooltipProps) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(e.target as Node) &&
        triggerRef.current &&
        !triggerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const handleKeyDown = (e: KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      setOpen((prev) => !prev);
    }
    if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <span className="source-tooltip-wrapper">
      <button
        ref={triggerRef}
        className="source-trigger"
        onClick={() => setOpen((prev) => !prev)}
        onKeyDown={handleKeyDown}
        aria-expanded={open}
        aria-label={`${sources.length} sources - click to view details`}
        type="button"
      >
        📌 {sources.length} {sources.length === 1 ? "source" : "sources"}
      </button>

      {open && (
        <div
          ref={popoverRef}
          className="source-popover"
          role="dialog"
          aria-label="Source attribution details"
        >
          {sources.map((source, i) => (
            <div key={i} className="source-item">
              <div className="source-header">
                <span className="source-doc-name">{source.documentName}</span>
                <span className="source-similarity">
                  {Math.round(source.similarityScore * 100)}% match
                </span>
              </div>
              {source.pageNumber !== null && (
                <span className="source-page">Page {source.pageNumber}</span>
              )}
              <p className="source-excerpt">{source.excerpt}</p>
              <a
                href={`/dashboard/knowledge?source=${encodeURIComponent(source.documentName)}`}
                className="source-link"
                tabIndex={0}
              >
                View in Knowledge Base
              </a>
            </div>
          ))}
        </div>
      )}
    </span>
  );
}
