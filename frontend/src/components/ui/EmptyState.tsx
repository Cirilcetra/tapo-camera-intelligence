import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center py-16 text-center",
        className
      )}
    >
      {Icon && (
        <div className="mb-4 rounded-full bg-zinc-800 p-4">
          <Icon className="h-8 w-8 text-zinc-500" />
        </div>
      )}
      <h3 className="mb-1 text-base font-semibold text-zinc-300">{title}</h3>
      {description && (
        <p className="mb-4 max-w-sm text-sm text-zinc-500">{description}</p>
      )}
      {action}
    </div>
  );
}
