/**
 * Wrapper component for EvidenceSeekerManagement to handle routing and UUID resolution
 */

import React, { useState, useEffect } from "react";
import { useParams } from "react-router";
import { EvidenceSeeker } from "../../types/evidenceSeeker";
import { useEvidenceSeekers } from "../../hooks/useEvidenceSeeker";
import EvidenceSeekerManagement from "./EvidenceSeekerManagement";

const EvidenceSeekerManagementWrapper: React.FC = () => {
  const { evidenceSeekerId } = useParams<{ evidenceSeekerId: string }>();
  const { evidenceSeekers } = useEvidenceSeekers();
  const [evidenceSeeker, setEvidenceSeeker] = useState<EvidenceSeeker | null>(
    null
  );

  useEffect(() => {
    if (evidenceSeekers.length > 0 && evidenceSeekerId) {
      // Find the evidence seeker by UUID or ID
      const seeker = evidenceSeekers.find(
        (es) =>
          es.uuid === evidenceSeekerId || es.id.toString() === evidenceSeekerId
      );
      setEvidenceSeeker(seeker || null);
    }
  }, [evidenceSeekers, evidenceSeekerId]);

  if (!evidenceSeeker) {
    return (
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="text-center">
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Loading Evidence Seeker...
            </h3>
            <p className="text-gray-500">
              Please wait while we load the evidence seeker details.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return <EvidenceSeekerManagement evidenceSeekerUuid={evidenceSeeker.uuid} />;
};

export default EvidenceSeekerManagementWrapper;
