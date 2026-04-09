"use client";

import { useState, useRef, useEffect, KeyboardEvent } from "react";
import clsx from "clsx";
import { ShieldCheck, ChevronDown, X } from "lucide-react";
import type { ClaimVerification } from "@/actions/scripts-lab";
import "./correction-badge.css";

interface CorrectionBadgeProps {
  correctionCount: number;
  verifiedClaims: ClaimVerification[];
  className?: string;
}

function truncateClaimText(text: string, maxLen: number = 50): string {
  if (!text) return "";
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen) + "...";
}

export function CorrectionBadge({
  correctionCount,
  verifiedClaims,
  className,
}: CorrectionBadgeProps) {
  const [expanded, setExpanded] = useState(false);
  const triggerRef = useRef<HTMLSpanElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const unsupportedClaims = verifiedClaims.filter((c) => !c.isSupported);

  useEffect(() => {
    if (!expanded) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (
        panelRef.current &&
        !panelRef.current.contains(e.target as Node) &&
        triggerRef.current &&
        !triggerRef.current.contains(e.target as Node)
      ) {
        setExpanded(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [expanded]);

  const handleTriggerKeyDown = (e: KeyboardEvent<HTMLSpanElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      setExpanded((prev) => !prev);
    }
    if (e.key === "Escape" && expanded) {
      setExpanded(false);
      triggerRef.current?.focus();
    }
  };

  const handlePanelKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape") {
      setExpanded(false);
      triggerRef.current?.focus();
    }
  };

  const displayCount = unsupportedClaims.length;

  return (
    <div className={clsx("correction-badge-wrapper", className)}>
      <span
        ref={triggerRef}
        className="correction-badge"
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        aria-label={`Corrected — ${correctionCount} ${correctionCount === 1 ? "claim" : "claims"} corrected`}
        onClick={() => setExpanded((prev) => !prev)}
        onKeyDown={handleTriggerKeyDown}
      >
        <ShieldCheck size={12} />
        <span>Corrected</span>
        <span className="correction-badge__count">({correctionCount})</span>
      </span>

      <div
        ref={panelRef}
        className={clsx(
          "correction-detail",
          expanded && "correction-detail--visible",
        )}
        aria-live="polite"
        aria-hidden={!expanded}
        onKeyDown={handlePanelKeyDown}
      >
        <div className="correction-detail__header">
          <span className="correction-detail__header-text">
            <ChevronDown size={12} className="correction-detail__chevron" />
            {displayCount} {displayCount === 1 ? "claim" : "claims"} corrected
          </span>
          <button
            className="correction-detail__close"
            onClick={() => setExpanded(false)}
            aria-label="Close correction details"
            type="button"
          >
            <X size={12} />
          </button>
        </div>

        {unsupportedClaims.map((claim, i) => (
          <div key={i} className="correction-detail__claim">
            {claim.verificationError ? (
              <span
                className="correction-detail__dot--unverified"
                aria-hidden="true"
              />
            ) : (
              <span
                className="correction-detail__dot--rephrased"
                aria-hidden="true"
              />
            )}
            <span className="correction-detail__status-label">
              {claim.verificationError ? "Could not verify" : "Rephrased"}
            </span>
            <span className="correction-detail__claim-text">
              {truncateClaimText(claim.claimText)}
            </span>
            <span className="correction-detail__similarity">
              {Math.round(claim.maxSimilarity * 100)}% match
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
