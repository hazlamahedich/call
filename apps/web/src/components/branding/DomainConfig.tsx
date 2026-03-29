"use client";

import { useState } from "react";
import { Link } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { StatusMessage } from "@/components/ui/status-message";
import type { DomainVerificationResult } from "@call/types";

interface DomainConfigProps {
  domain: string | null;
  verified: boolean;
  onVerify: (domain: string) => Promise<DomainVerificationResult | null>;
}

type Status = "idle" | "verifying" | "success" | "error";

export function DomainConfig({
  domain,
  verified,
  onVerify,
}: DomainConfigProps) {
  const [input, setInput] = useState(domain ?? "");
  const [status, setStatus] = useState<Status>(verified ? "success" : "idle");
  const [result, setResult] = useState<DomainVerificationResult | null>(null);

  const handleVerify = async () => {
    if (!input.trim()) return;
    setStatus("verifying");
    setResult(null);
    try {
      const res = await onVerify(input.trim());
      if (res) {
        setResult(res);
        setStatus(res.verified ? "success" : "error");
      } else {
        setStatus("error");
        setResult({ verified: false, message: "Verification failed" });
      }
    } catch {
      setStatus("error");
      setResult({ verified: false, message: "Verification failed" });
    }
  };

  return (
    <Card variant="standard" className="p-0">
      <CardContent className="p-md">
        <div className="flex items-end gap-sm">
          <div className="flex-1">
            <label className="mb-xs block text-xs text-muted-foreground">
              Custom Domain (CNAME)
            </label>
            <div className="flex items-center gap-sm">
              <Link className="size-4 shrink-0 text-muted-foreground" />
              <Input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="custom.yourdomain.com"
              />
            </div>
          </div>
          <Button
            variant="primary"
            size="md"
            onClick={handleVerify}
            disabled={status === "verifying" || !input.trim()}
          >
            {status === "verifying" ? "Verifying..." : "Verify DNS"}
          </Button>
        </div>

        {status === "success" && (
          <StatusMessage variant="success" className="mt-sm">
            Domain verified successfully
          </StatusMessage>
        )}

        {status === "error" && result && (
          <>
            <StatusMessage variant="error" className="mt-sm">
              {result.message}
            </StatusMessage>
            {result.instructions && (
              <Card variant="glass" className="mt-sm p-sm">
                <code className="text-xs text-muted-foreground">
                  {result.instructions}
                </code>
              </Card>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
