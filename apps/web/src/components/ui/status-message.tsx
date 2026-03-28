import * as React from "react";
import { cn } from "@/lib/utils";
import { CheckCircle, AlertTriangle, XCircle, Info } from "lucide-react";

const statusVariants = {
  success: {
    container: "border-neon-emerald/30 bg-neon-emerald/5 text-neon-emerald",
    icon: CheckCircle,
  },
  warning: {
    container: "border-neon-blue/30 bg-neon-blue/5 text-neon-blue",
    icon: AlertTriangle,
  },
  error: {
    container: "border-destructive/30 bg-destructive/5 text-destructive",
    icon: XCircle,
  },
  info: {
    container: "border-muted-foreground/30 bg-muted/50 text-muted-foreground",
    icon: Info,
  },
} as const;

export interface StatusMessageProps extends React.HTMLAttributes<HTMLDivElement> {
  variant: keyof typeof statusVariants;
}

const StatusMessage = React.forwardRef<HTMLDivElement, StatusMessageProps>(
  ({ className, variant, children, ...props }, ref) => {
    const { container, icon: Icon } = statusVariants[variant];

    return (
      <div
        ref={ref}
        role="status"
        className={cn(
          "flex items-center gap-sm rounded-md border p-md text-sm",
          container,
          className,
        )}
        {...props}
      >
        <Icon className="size-4 shrink-0" />
        <span>{children}</span>
      </div>
    );
  },
);
StatusMessage.displayName = "StatusMessage";

export { StatusMessage, statusVariants };
