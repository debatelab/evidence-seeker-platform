import React, { useState, useEffect } from "react";
import { Link, useLocation } from "react-router";
import { EvidenceSeeker } from "../../types/evidenceSeeker";
import { useEvidenceSeekers } from "../../hooks/useEvidenceSeeker";
import PageLayout from "../PageLayout";

const EvidenceSeekerList: React.FC = () => {
  const { evidenceSeekers, loading, error, deleteEvidenceSeeker } =
    useEvidenceSeekers();
  const [deleteLoading, setDeleteLoading] = useState<number | null>(null);
  const location = useLocation();
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    // Check if there's a success message in the location state
    if (location.state?.message) {
      setSuccessMessage(location.state.message);
      // Clear the message after 5 seconds
      const timer = setTimeout(() => setSuccessMessage(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [location.state]);

  const handleDelete = async (id: number) => {
    setDeleteLoading(id);
    const success = await deleteEvidenceSeeker(id);
    if (!success) {
      alert("Failed to delete evidence seeker");
    }
    setDeleteLoading(null);
  };

  if (loading) {
    return (
      <PageLayout variant="wide">
        <div className="flex justify-center items-center p-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </PageLayout>
    );
  }

  if (error) {
    return (
      <PageLayout variant="wide">
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="text-red-800">{error}</div>
        </div>
      </PageLayout>
    );
  }

  if (evidenceSeekers.length === 0) {
    return (
      <PageLayout variant="wide">
        <div className="text-center py-12">
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No Evidence Seekers
          </h3>
          <p className="text-gray-500 mb-4">
            Get started by creating your first evidence seeker.
          </p>
          <Link
            to="/evidence-seekers/new"
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 inline-block"
          >
            Create Evidence Seeker
          </Link>
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout variant="wide">
      <div className="space-y-4">
        {/* Success Message */}
        {successMessage && (
          <div className="bg-green-50 border border-green-200 rounded-md p-4">
            <div className="text-green-800 flex items-center">
              <svg
                className="w-5 h-5 mr-2"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
              {successMessage}
            </div>
          </div>
        )}

        <div className="flex justify-between items-center">
          <h2 className="text-xl font-semibold text-gray-900">
            Evidence Seekers
          </h2>
          <Link
            to="/evidence-seekers/new"
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
          >
            Create New
          </Link>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {evidenceSeekers.map((seeker) => (
            <div
              key={seeker.id}
              className="bg-white border border-gray-200 rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex justify-between items-start mb-4">
                <h3 className="text-lg font-medium text-gray-900 truncate">
                  {seeker.title}
                </h3>
                <span
                  className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    seeker.isPublic
                      ? "bg-green-100 text-green-800"
                      : "bg-yellow-100 text-yellow-800"
                  }`}
                >
                  {seeker.isPublic ? "Public" : "Private"}
                </span>
              </div>

              <p className="text-gray-600 text-sm mb-4 line-clamp-3">
                {seeker.description}
              </p>

              <div className="flex justify-between items-center text-xs text-gray-500 mb-4">
                <span>
                  Created {new Date(seeker.createdAt).toLocaleDateString()}
                </span>
              </div>

              <div className="flex space-x-2">
                <Link
                  to={`/evidence-seekers/${seeker.uuid}/manage`}
                  className="flex-1 bg-blue-600 text-white px-3 py-2 rounded-md text-sm hover:bg-blue-700 text-center"
                >
                  Manage
                </Link>
                <button
                  onClick={() => handleDelete(seeker.id)}
                  disabled={deleteLoading === seeker.id}
                  className="flex-1 bg-red-600 text-white px-3 py-2 rounded-md text-sm hover:bg-red-700 disabled:opacity-50 text-center"
                >
                  {deleteLoading === seeker.id ? "..." : "Delete"}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </PageLayout>
  );
};

export default EvidenceSeekerList;
