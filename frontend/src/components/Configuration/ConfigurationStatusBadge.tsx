import React from "react";
import { ShieldAlert, CheckCircle2, Hourglass } from "lucide-react";
import type { ConfigurationState } from "../../types/evidenceSeeker";

interface ConfigurationStatusBadgeProps {
  state: ConfigurationState | null | undefined;
  className?: string;
}

const toneByState: Record<
  ConfigurationState,
  { classes: string; label: string; Icon: React.ComponentType<{ className?: string }> }
> = {
  READY: {
    classes: "bg-green-100 text-green-800 border-green-200",
    label: "Configuration complete",
    Icon: CheckCircle2,
  },
  MISSING_CREDENTIALS: {
    classes: "bg-amber-100 text-amber-800 border-amber-200",
    label: "Action required",
    Icon: ShieldAlert,
  },
  MISSING_DOCUMENTS: {
    classes: "bg-orange-100 text-orange-800 border-orange-200",
    label: "Upload documents",
    Icon: ShieldAlert,
  },
  UNCONFIGURED: {
    classes: "bg-gray-100 text-gray-700 border-gray-200",
    label: "Needs setup",
    Icon: Hourglass,
  },
  ERROR: {
    classes: "bg-red-100 text-red-800 border-red-200",
    label: "Configuration error",
    Icon: ShieldAlert,
  },
};

export const ConfigurationStatusBadge: React.FC<ConfigurationStatusBadgeProps> = ({
  state,
  className = "",
}) => {
  if (!state) {
    return null;
  }
  const tone = toneByState[state];
  if (!tone) {
    return null;
  }
  const Icon = tone.Icon;
  return (
    <span
      className={`inline-flex items-center space-x-1 px-2.5 py-1 rounded-full border text-xs font-medium ${tone.classes} ${className}`}
    >
      <Icon className="h-3.5 w-3.5" />
      <span>{tone.label}</span>
    </span>
  );
};

export default ConfigurationStatusBadge;
