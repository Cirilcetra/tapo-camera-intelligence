import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

interface SpinnerProps {
  className?: string;
  size?: number;
}

export function Spinner({ className, size = 20 }: SpinnerProps) {
  return (
    <Loader2
      className={cn("animate-spin text-zinc-400", className)}
      size={size}
    />
  );
}
