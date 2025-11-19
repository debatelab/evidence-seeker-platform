import type { ComponentType } from "react";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  CircleSlash2,
  HelpCircle,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import type { FactCheckResult } from "../types/factCheck";

type ConfirmationDisplay = {
  label: string;
  bg: string;
  text: string;
  border: string;
  icon: ComponentType<{ className?: string }>;
};

export type ConfirmationSummaryDisplay = ConfirmationDisplay & {
  key: string;
  count: number;
};

const confirmationLevelStyles: Record<string, ConfirmationDisplay> = {
  strongly_confirmed: {
    label: "Strongly confirmed",
    bg: "bg-emerald-50",
    text: "text-emerald-800",
    border: "border-emerald-200",
    icon: ShieldCheck,
  },
  confirmed: {
    label: "Confirmed",
    bg: "bg-green-50",
    text: "text-green-800",
    border: "border-green-200",
    icon: CheckCircle2,
  },
  weakly_confirmed: {
    label: "Weakly confirmed",
    bg: "bg-lime-50",
    text: "text-lime-800",
    border: "border-lime-200",
    icon: CheckCircle2,
  },
  inconclusive_confirmation: {
    label: "Inconclusive confirmation",
    bg: "bg-amber-50",
    text: "text-amber-800",
    border: "border-amber-200",
    icon: AlertCircle,
  },
  weakly_disconfirmed: {
    label: "Weakly disconfirmed",
    bg: "bg-orange-50",
    text: "text-orange-800",
    border: "border-orange-200",
    icon: CircleSlash2,
  },
  disconfirmed: {
    label: "Disconfirmed",
    bg: "bg-red-50",
    text: "text-red-800",
    border: "border-red-200",
    icon: XCircle,
  },
  strongly_disconfirmed: {
    label: "Strongly disconfirmed",
    bg: "bg-rose-50",
    text: "text-rose-800",
    border: "border-rose-200",
    icon: AlertTriangle,
  },
};

const fallbackConfirmationStyle: ConfirmationDisplay = {
  label: "Pending interpretation",
  bg: "bg-gray-100",
  text: "text-gray-700",
  border: "border-gray-200",
  icon: HelpCircle,
};

const getConfirmationDisplay = (
  level?: string | null
): ConfirmationDisplay & { key: string } => {
  if (!level) {
    return { key: "pending", ...fallbackConfirmationStyle };
  }
  const normalized = level.toLowerCase();
  if (confirmationLevelStyles[normalized]) {
    return { key: normalized, ...confirmationLevelStyles[normalized] };
  }
  return { key: normalized, ...fallbackConfirmationStyle, label: level };
};

export const aggregateResultSummary = (
  results: FactCheckResult[]
): ConfirmationSummaryDisplay[] => {
  if (!results.length) return [];
  const summaryMap: Record<string, ConfirmationSummaryDisplay> = {};
  results.forEach((result) => {
    const display = getConfirmationDisplay(result.confirmationLevel);
    if (!summaryMap[display.key]) {
      summaryMap[display.key] = { ...display, count: 0 };
    }
    summaryMap[display.key].count += 1;
  });
  return Object.values(summaryMap).sort((a, b) => b.count - a.count);
};
