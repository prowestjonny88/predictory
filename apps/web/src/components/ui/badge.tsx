import { cn } from "@/lib/utils";

export type BadgeVariant =
  | "default"
  | "critical"
  | "high"
  | "medium"
  | "low"
  | "success"
  | "outline"
  | "draft"
  | "approved"
  | "info";

const variantClasses: Record<BadgeVariant, string> = {
  default:  "bg-neutral-100 text-neutral-700 border-neutral-200",
  critical: "bg-red-100 text-red-700 border-red-200",
  high:     "bg-orange-100 text-orange-700 border-orange-200",
  medium:   "bg-yellow-100 text-yellow-700 border-yellow-200",
  low:      "bg-green-100 text-green-700 border-green-200",
  success:  "bg-green-100 text-green-700 border-green-200",
  outline:  "bg-transparent text-neutral-600 border-neutral-300",
  draft:    "bg-yellow-50 text-yellow-700 border-yellow-200",
  approved: "bg-green-50 text-green-700 border-green-300",
  info:     "bg-sky-100 text-sky-700 border-sky-200",
};

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

export function Badge({ children, variant = "default", className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold leading-none",
        variantClasses[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
