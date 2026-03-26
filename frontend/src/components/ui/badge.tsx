import * as React from "react"
import { type VariantProps } from "class-variance-authority"
import { Slot } from "radix-ui"

import { cn } from "@/lib/utils"
import { badgeVariants } from "./badge-variants"

function Badge({
  className,
  variant = "default",
  appearance,
  asChild = false,
  ...props
}: React.ComponentProps<"span"> &
  VariantProps<typeof badgeVariants> & { asChild?: boolean; appearance?: "stroke" }) {
  const Comp = asChild ? Slot.Root : "span"

  const strokeStyles = appearance === "stroke"
    ? "border-brand-8 bg-transparent text-brand-8"
    : ""

  return (
    <Comp
      data-slot="badge"
      data-variant={variant}
      className={cn(badgeVariants({ variant }), strokeStyles, className)}
      {...props}
    />
  )
}

export { Badge }
