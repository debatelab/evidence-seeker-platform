import React from "react";
import { Link } from "react-router";
import type { PublicEvidenceSeekerSummary } from "../../types/public";

interface EvidenceSeekerCardProps {
  seeker: PublicEvidenceSeekerSummary;
}

const EvidenceSeekerCard: React.FC<EvidenceSeekerCardProps> = ({ seeker }) => {
  return (
    <Link
      to={`/evidence-seekers/${seeker.uuid}`}
      className="block rounded-lg border border-gray-100 bg-white p-6 shadow-sm transition hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
    >
      <div className="flex items-center space-x-3 mb-4">
        <div className="h-10 w-10 rounded-full bg-primary-soft text-primary flex items-center justify-center font-semibold">
          {seeker.title.slice(0, 2).toUpperCase()}
        </div>
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Evidence Seeker
          </p>
          <p className="text-lg font-semibold text-gray-900">{seeker.title}</p>
        </div>
      </div>
      <p className="text-sm text-gray-600 mb-4 line-clamp-3">
        {seeker.description || "No description yet."}
      </p>
      <dl className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <dt className="text-gray-500">Documents</dt>
          <dd className="font-semibold text-gray-900">{seeker.documentCount}</dd>
        </div>
        <div>
          <dt className="text-gray-500">Last fact check</dt>
          <dd className="font-semibold text-gray-900">
            {seeker.latestFactCheckAt
              ? new Date(seeker.latestFactCheckAt).toLocaleDateString()
              : "—"}
          </dd>
        </div>
      </dl>
      <p className="mt-4 text-sm font-semibold text-primary">
        Test this seeker →
      </p>
    </Link>
  );
};

export default EvidenceSeekerCard;
