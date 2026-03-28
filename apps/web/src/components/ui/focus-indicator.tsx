import * as React from "react";
import { cn } from "@/lib/utils";

export interface FocusIndicatorProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

const FocusIndicator = React.forwardRef<HTMLDivElement, FocusIndicatorProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "rounded-md focus-within:outline-none focus-within:ring-2 focus-within:ring-ring",
          className,
        )}
        {...props}
      >
        {children}
      </div>
    );
  },
);
FocusIndicator.displayName = "FocusIndicator";

export { FocusIndicator };
