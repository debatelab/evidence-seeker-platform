import React from "react";
import EvidenceSeekerSettings from "./EvidenceSeekerSettings";
import EvidenceSeekerConfig from "./EvidenceSeekerConfig";

interface EvidenceSeekerSettingsAndConfigProps {
  evidenceSeekerUuid: string;
}

const EvidenceSeekerSettingsAndConfig: React.FC<
  EvidenceSeekerSettingsAndConfigProps
> = ({ evidenceSeekerUuid }) => {
  return (
    <div className="space-y-8">
      <EvidenceSeekerSettings evidenceSeekerUuid={evidenceSeekerUuid} />
      <EvidenceSeekerConfig evidenceSeekerUuid={evidenceSeekerUuid} />
    </div>
  );
};

export default EvidenceSeekerSettingsAndConfig;
