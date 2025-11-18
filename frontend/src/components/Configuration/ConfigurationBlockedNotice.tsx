import React from "react";
import { AlertCircle, ArrowRight } from "lucide-react";
import type { ConfigurationStatus } from "../../types/evidenceSeeker";

interface ConfigurationBlockedNoticeProps {
  status: ConfigurationStatus | null;
  onConfigure?: () => void;
  title?: string;
  description?: string;
}

const requirementCopy: Record<string, string> = {
  CREDENTIALS: "Add inference credentials (Hugging Face key + billing, if required)",
  DOCUMENTS: "Upload at least one document to finish setup",
};

export const ConfigurationBlockedNotice: React.FC<
  ConfigurationBlockedNoticeProps
> = ({ status, onConfigure, title, description }) => {
  const headline = title ?? "Configuration required";
  const explainer =
    description ??
    "Complete the quick setup wizard before uploading documents or running analysis.";
  const missing = status?.missingRequirements ?? [];

  return (
    <div className="bg-white border border-amber-200 rounded-xl shadow-sm p-8 text-center space-y-4">
      <div className="inline-flex items-center justify-center rounded-full bg-amber-100 text-amber-700 h-12 w-12">
        <AlertCircle className="h-6 w-6" aria-hidden="true" />
      </div>
      <div className="space-y-2">
        <h3 className="text-xl font-semibold text-gray-900">{headline}</h3>
        <p className="text-gray-600 max-w-xl mx-auto">{explainer}</p>
      </div>
      {missing.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-900 max-w-xl mx-auto text-left">
          <p className="font-medium mb-2">Next steps</p>
          <ul className="list-disc list-inside space-y-1">
            {missing.map((item) => (
              <li key={item}>
                {requirementCopy[item] ?? item.replaceAll("_", " ").toLowerCase()}
              </li>
            ))}
          </ul>
        </div>
      )}
      {onConfigure && (
        <button
          onClick={onConfigure}
          className="inline-flex items-center justify-center bg-blue-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 transition"
        >
          Open configuration
          <ArrowRight className="h-4 w-4 ml-2" />
        </button>
      )}
    </div>
  );
};

export default ConfigurationBlockedNotice;
