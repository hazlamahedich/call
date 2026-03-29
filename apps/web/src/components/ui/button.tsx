import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary:
          "bg-neon-emerald text-background shadow-glow-emerald hover:bg-neon-emerald/90",
        secondary:
          "border border-border bg-transparent text-foreground hover:bg-muted",
        destructive:
          "border border-destructive/50 bg-transparent text-destructive hover:bg-destructive/10",
        ghost: "text-muted-foreground hover:text-foreground hover:bg-muted",
      },
      size: {
        sm: "h-8 px-sm text-xs",
        md: "h-10 px-md text-sm",
        lg: "h-12 px-lg text-base",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

export interface ButtonProps
  extends
    React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
