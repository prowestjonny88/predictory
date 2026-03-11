import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function todayISO(): string {
  return new Date().toISOString().split("T")[0];
}

export function scoreToRisk(score?: number | null): "low" | "medium" | "high" {
  if (score == null) return "low";
  if (score < 30) return "low";
  if (score < 60) return "medium";
  return "high";
}
