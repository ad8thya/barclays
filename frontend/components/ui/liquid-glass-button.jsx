"use client";

import { Slot } from "@radix-ui/react-slot";
import { cva } from "class-variance-authority";
import { cn } from "@/lib/cn";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-medium transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "bg-accent text-white shadow-lg shadow-accent/20 hover:bg-accent-light hover:shadow-xl hover:shadow-accent/30 active:scale-[0.98]",
        ghost:
          "text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]",
        outline:
          "border border-white/[0.08] bg-transparent text-slate-300 hover:bg-white/[0.04] hover:border-white/[0.12]",
      },
      size: {
        default: "h-12 px-8",
        sm: "h-9 px-4 text-xs",
        lg: "h-14 px-12 text-base",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export function LiquidButton({
  className,
  variant,
  size,
  asChild = false,
  ...props
}) {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}
