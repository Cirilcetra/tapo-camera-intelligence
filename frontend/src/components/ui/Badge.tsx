import { cn } from "@/lib/utils";

type Variant = "default" | "success" | "warning" | "error" | "info";

const variantStyles: Record<Variant, string> = {
  default: "bg-zinc-700 text-zinc-200",
  success: "bg-emerald-900/60 text-emerald-300 border border-emerald-700/40",
  warning: "bg-amber-900/60 text-amber-300 border border-amber-700/40",
  error: "bg-red-900/60 text-red-300 border border-red-700/40",
  info: "bg-blue-900/60 text-blue-300 border border-blue-700/40",
};

interface BadgeProps {
  variant?: Variant;
  children: React.ReactNode;
  className?: string;
}

export function Badge({ variant = "default", children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        variantStyles[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
