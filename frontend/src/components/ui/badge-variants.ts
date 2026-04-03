import { cva } from "class-variance-authority"

export const badgeVariants = cva(
  "inline-flex w-fit shrink-0 items-center justify-center gap-1 overflow-hidden rounded-full border border-transparent px-2 py-0.5 text-xs font-medium whitespace-nowrap transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 [&>svg]:pointer-events-none [&>svg]:size-3",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground [a&]:hover:bg-primary/90",
        secondary:
          "bg-secondary text-secondary-foreground [a&]:hover:bg-secondary/90",
        destructive:
          "bg-red-500/25 text-red-300 border-red-500/40 font-semibold focus-visible:ring-destructive/20 [a&]:hover:bg-destructive/90",
        outline:
          "border-border text-foreground [a&]:hover:bg-accent [a&]:hover:text-accent-foreground",
        ghost: "[a&]:hover:bg-accent [a&]:hover:text-accent-foreground",
        link: "text-primary underline-offset-4 [a&]:hover:underline",
        primary: "bg-brand-1 text-white border-brand-1/20",
        success:
          "bg-brand-9/25 text-brand-9 border-brand-9/40 font-semibold",
        warning:
          "bg-amber-500/25 text-amber-300 border-amber-500/40 font-semibold",
        info:
          "bg-blue-500/25 text-blue-300 border-blue-500/40 font-semibold",
        mono:
          "bg-white/10 text-white/90 border-white/20 font-semibold",
        "mono-light":
          "bg-[#e8e0d0]/60 text-[#4a4a4a] border-[#d0c8b8] font-semibold",
        "success-light":
          "bg-emerald-50 text-emerald-700 border-emerald-200 font-semibold",
        "warning-light":
          "bg-amber-50 text-amber-700 border-amber-200 font-semibold",
        "destructive-light":
          "bg-red-50 text-red-700 border-red-200 font-semibold",
        "info-light":
          "bg-blue-50 text-blue-700 border-blue-200 font-semibold",
        stroke:
          "border-brand-8 bg-transparent text-brand-8",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)
