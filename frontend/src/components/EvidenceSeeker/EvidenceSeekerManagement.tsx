/**
 * Evidence Seeker Management component with tabs for documents and admin settings
 */

import React, { useState, useEffect } from "react";
import { Link, useLocation, useNavigate, Outlet } from "react-router";
import {
  FileText,
  Settings,
  ArrowLeft,
  Database,
  Users,
  ShieldCheck,
} from "lucide-react";
import { EvidenceSeeker } from "../../types/evidenceSeeker";
import { useEvidenceSeekers } from "../../hooks/useEvidenceSeeker";
import PageLayout from "../PageLayout";
import { useConfigurationStatus } from "../../hooks/useConfigurationStatus";
import { ConfigurationStatusBadge } from "../Configuration/ConfigurationStatusBadge";

interface EvidenceSeekerManagementProps {
  evidenceSeekerUuid: string;
}

type TabType =
  | "documents"
  | "fact-checks"
  | "settings"
  | "users";

const EvidenceSeekerManagement: React.FC<EvidenceSeekerManagementProps> = ({
  evidenceSeekerUuid,
}) => {
  const { evidenceSeekers } = useEvidenceSeekers();
  const location = useLocation();
  const navigate = useNavigate();
  const [evidenceSeeker, setEvidenceSeeker] = useState<EvidenceSeeker | null>(
    null
  );
  const { status: configurationStatus } =
    useConfigurationStatus(evidenceSeekerUuid);

  const tabs = [
    {
      id: "documents" as TabType,
      label: "Documents",
      icon: FileText,
      description: "Manage documents and uploads",
    },
    {
      id: "fact-checks" as TabType,
      label: "Fact Checks",
      icon: ShieldCheck,
      description: "Submit statements and inspect fact-check runs",
    },
    {
      id: "settings" as TabType,
      label: "Settings & Configuration",
      icon: Settings,
      description: "Manage basics, visibility, and pipeline configuration",
    },
    {
      id: "users" as TabType,
      label: "User Management",
      icon: Users,
      description: "Manage who can access and modify this evidence seeker",
    },
  ];

  useEffect(() => {
    if (evidenceSeekers.length > 0 && evidenceSeekerUuid) {
      // Find the evidence seeker by UUID
      const seeker = evidenceSeekers.find(
        (es) => es.uuid === evidenceSeekerUuid
      );
      setEvidenceSeeker(seeker || null);
    }
  }, [evidenceSeekers, evidenceSeekerUuid]);

  // Get current tab from URL
  const getActiveTabFromPath = (): TabType => {
    const pathParts = location.pathname.split("/");
    const lastPart = pathParts[pathParts.length - 1];
    return (
      (tabs.find((tab) => tab.id === lastPart)?.id as TabType) || "documents"
    );
  };

  const activeTab = getActiveTabFromPath();

  if (!evidenceSeeker) {
    return (
      <PageLayout variant="wide">
        <div className="flex justify-center items-center p-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-gray-600">Loading Evidence Seeker...</span>
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout variant="wide">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Link
              to="/app/evidence-seekers"
              className="flex items-center text-gray-600 hover:text-gray-900"
            >
              <ArrowLeft className="h-5 w-5 mr-2" />
              Back to Evidence Seekers
            </Link>
          </div>
          <ConfigurationStatusBadge
            state={configurationStatus?.state ?? null}
          />
        </div>

        {/* Evidence Seeker Info */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="brand-title text-2xl text-gray-900">
                {evidenceSeeker.title}
              </h1>
              <p className="text-gray-600 mt-1">{evidenceSeeker.description}</p>
              <div className="flex items-center space-x-4 mt-3">
                <span
                  className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    evidenceSeeker.isPublic
                      ? "bg-green-100 text-green-800"
                      : "bg-yellow-100 text-yellow-800"
                  }`}
                >
                  {evidenceSeeker.isPublic ? "Public" : "Private"}
                </span>
                <span className="text-sm text-gray-500">
                  Created{" "}
                  {new Date(evidenceSeeker.createdAt).toLocaleDateString()}
                </span>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Database className="h-5 w-5 text-blue-600" />
              <span className="text-sm text-gray-600">Evidence Seeker</span>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="border-b border-gray-200">
            <nav className="flex space-x-8 px-6" aria-label="Tabs">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => navigate(tab.id)}
                    className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm ${
                      activeTab === tab.id
                        ? "border-blue-500 text-blue-600"
                        : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {/* Tab Description */}
            <div className="mb-6">
              {tabs.map((tab) => {
                if (tab.id === activeTab) {
                  const Icon = tab.icon;
                  return (
                    <div
                      key={tab.id}
                      className="flex items-center space-x-3 p-4 bg-blue-50 rounded-lg border border-blue-200"
                    >
                      <Icon className="h-5 w-5 text-blue-600" />
                      <div>
                        <h3 className="text-sm font-medium text-blue-900">
                          {tab.label}
                        </h3>
                        <p className="text-sm text-blue-700">
                          {tab.description}
                        </p>
                      </div>
                    </div>
                  );
                }
                return null;
              })}
            </div>

            {/* Content */}
            <Outlet />
          </div>
        </div>
      </div>
    </PageLayout>
  );
};

export default EvidenceSeekerManagement;
