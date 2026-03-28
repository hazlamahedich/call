import * as React from "react";
import { cn } from "@/lib/utils";
import { Inbox } from "lucide-react";

export interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  icon?: React.ElementType;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

const EmptyState = React.forwardRef<HTMLDivElement, EmptyStateProps>(
  (
    { className, icon: Icon = Inbox, title, description, action, ...props },
    ref,
  ) => {
    return (
      <div
        ref={ref}
        className={cn(
          "flex flex-col items-center justify-center rounded-lg border border-dashed border-border p-xl text-center",
          className,
        )}
        {...props}
      >
        <Icon className="size-10 text-muted-foreground/50 mb-md" />
        <h3 className="text-sm font-medium text-foreground mb-xs">{title}</h3>
        {description && (
          <p className="text-xs text-muted-foreground max-w-xs">
            {description}
          </p>
        )}
        {action && <div className="mt-md">{action}</div>}
      </div>
    );
  },
);
EmptyState.displayName = "EmptyState";

export { EmptyState };
