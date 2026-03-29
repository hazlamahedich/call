"use client";

import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { cn } from "@/lib/utils";
import { AlertTriangle, Info } from "lucide-react";
import { Button } from "./button";

export interface ConfirmActionProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  variant?: "destructive" | "neutral";
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  children: React.ReactNode;
}

function ConfirmAction({
  open,
  onOpenChange,
  variant = "destructive",
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  onConfirm,
  children,
}: ConfirmActionProps) {
  const Icon = variant === "destructive" ? AlertTriangle : Info;

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Trigger asChild>{children}</DialogPrimitive.Trigger>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay
          className={cn(
            "fixed inset-0 z-50 bg-background/80 backdrop-blur-sm",
            "data-[state=open]:animate-in data-[state=closed]:animate-out",
            "data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
          )}
        />
        <DialogPrimitive.Content
          className={cn(
            "fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2",
            "w-full max-w-md rounded-lg border border-border bg-card p-lg",
            "shadow-[0_0_30px_rgba(0,0,0,0.5)]",
            "data-[state=open]:animate-in data-[state=closed]:animate-out",
            "data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
            "data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95",
          )}
        >
          <div className="flex items-start gap-md">
            <div
              className={cn(
                "flex size-10 shrink-0 items-center justify-center rounded-full border",
                variant === "destructive"
                  ? "border-destructive/30 bg-destructive/10 text-destructive"
                  : "border-neon-blue/30 bg-neon-blue/10 text-neon-blue",
              )}
            >
              <Icon className="size-5" />
            </div>
            <div className="flex-1 space-y-xs">
              <DialogPrimitive.Title className="text-sm font-semibold text-foreground">
                {title}
              </DialogPrimitive.Title>
              <DialogPrimitive.Description className="text-xs text-muted-foreground">
                {description}
              </DialogPrimitive.Description>
            </div>
          </div>
          <div className="mt-lg flex justify-end gap-sm">
            <DialogPrimitive.Close asChild>
              <Button variant="secondary" size="sm">
                {cancelLabel}
              </Button>
            </DialogPrimitive.Close>
            <DialogPrimitive.Close asChild>
              <Button
                variant={variant === "destructive" ? "destructive" : "primary"}
                size="sm"
                onClick={onConfirm}
              >
                {confirmLabel}
              </Button>
            </DialogPrimitive.Close>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

export { ConfirmAction };
