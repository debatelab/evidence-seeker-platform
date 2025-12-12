/**
 * Evidence Seeker Settings component for editing basic information
 */

import React, { useState, useEffect } from "react";
import { Settings, Save, X } from "lucide-react";
import {
  EvidenceSeeker,
  EvidenceSeekerUpdate,
} from "../../types/evidenceSeeker";
import { useEvidenceSeekers } from "../../hooks/useEvidenceSeeker";
import {
  DEFAULT_LANGUAGE,
  SUPPORTED_LANGUAGES,
  SupportedLanguageCode,
  getLanguageLabel,
} from "../../constants/languages";

interface EvidenceSeekerSettingsProps {
  evidenceSeekerUuid: string;
}

const EvidenceSeekerSettings: React.FC<EvidenceSeekerSettingsProps> = ({
  evidenceSeekerUuid,
}) => {
  const { evidenceSeekers, updateEvidenceSeeker } = useEvidenceSeekers();
  const [evidenceSeeker, setEvidenceSeeker] = useState<EvidenceSeeker | null>(
    null
  );
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const [formData, setFormData] = useState({
    title: "",
    description: "",
    isPublic: false,
    factCheckPublicationMode: "AUTOPUBLISH",
    language: DEFAULT_LANGUAGE,
  });

  useEffect(() => {
    if (evidenceSeekers.length > 0 && evidenceSeekerUuid) {
      const seeker = evidenceSeekers.find(
        (es) => es.uuid === evidenceSeekerUuid
      );
      if (seeker) {
        setEvidenceSeeker(seeker);
        setFormData({
          title: seeker.title || "",
          description: seeker.description || "",
          isPublic: seeker.isPublic || false,
          factCheckPublicationMode:
            seeker.factCheckPublicationMode || "AUTOPUBLISH",
          language:
            (seeker.language as SupportedLanguageCode) || DEFAULT_LANGUAGE,
        });
      }
    }
  }, [evidenceSeekers, evidenceSeekerUuid]);

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.title.trim()) {
      newErrors.title = "Title is required";
    } else if (formData.title.length > 100) {
      newErrors.title = "Title must be 100 characters or less";
    }

    if (formData.description.length > 500) {
      newErrors.description = "Description must be 500 characters or less";
    }

    const supportedLanguageValues = SUPPORTED_LANGUAGES.map(
      (option) => option.value
    );
    if (
      !formData.language ||
      !supportedLanguageValues.includes(formData.language)
    ) {
      newErrors.language = "Select a supported language.";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    if (!evidenceSeeker || !validateForm()) {
      return;
    }

    setLoading(true);

    try {
      const updateData: EvidenceSeekerUpdate = {
        title: formData.title,
        description: formData.description,
        isPublic: formData.isPublic,
        factCheckPublicationMode: formData.factCheckPublicationMode as EvidenceSeeker["factCheckPublicationMode"],
        language: formData.language || null,
      };

      const success = await updateEvidenceSeeker(evidenceSeeker.id, updateData);

      if (success) {
        setIsEditing(false);
        // Update local state
        setEvidenceSeeker({
          ...evidenceSeeker,
          title: formData.title,
          description: formData.description,
          isPublic: formData.isPublic,
          factCheckPublicationMode:
            formData.factCheckPublicationMode as EvidenceSeeker["factCheckPublicationMode"],
          language: formData.language,
        });
      } else {
        setErrors({ general: "Failed to update evidence seeker" });
      }
    } catch (error) {
      setErrors({ general: "An error occurred while updating" });
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    if (evidenceSeeker) {
      setFormData({
        title: evidenceSeeker.title || "",
        description: evidenceSeeker.description || "",
        isPublic: evidenceSeeker.isPublic || false,
        factCheckPublicationMode:
          evidenceSeeker.factCheckPublicationMode || "AUTOPUBLISH",
        language:
          (evidenceSeeker.language as SupportedLanguageCode) ||
          DEFAULT_LANGUAGE,
      });
    }
    setIsEditing(false);
    setErrors({});
  };

  const handleInputChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: "" }));
    }
  };

  const handleCheckboxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, checked } = e.target;
    setFormData((prev) => ({ ...prev, [name]: checked }));
  };

  if (!evidenceSeeker) {
    return (
      <div className="flex justify-center items-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading settings...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Settings className="h-6 w-6 text-blue-600" />
          <div>
            <h4 className="text-md font-semibold text-gray-900">
              Basic Settings
            </h4>
            <p className="text-sm text-gray-600">
              Manage basic information and visibility settings
            </p>
          </div>
        </div>

        {!isEditing && (
          <button
            onClick={() => setIsEditing(true)}
            className="btn-primary px-4 py-2 flex items-center space-x-2"
          >
            <Settings className="h-4 w-4" />
            <span>Edit Settings</span>
          </button>
        )}
      </div>

      {/* Error Display */}
      {errors.general && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800">{errors.general}</div>
        </div>
      )}

      {/* Settings Form */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="p-6">
          {isEditing ? (
            // Edit Mode
            <div className="space-y-6">
              <div>
                <label
                  htmlFor="title"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Title *
                </label>
                <input
                  type="text"
                  id="title"
                  name="title"
                  value={formData.title}
                  onChange={handleInputChange}
                  className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    errors.title ? "border-red-300" : "border-gray-300"
                  }`}
                  placeholder="Enter a title for your evidence seeker"
                />
                {errors.title && (
                  <p className="mt-1 text-sm text-red-600">{errors.title}</p>
                )}
                <p className="mt-1 text-sm text-gray-500">
                  {formData.title.length}/100 characters
                </p>
              </div>

              <div>
                <label
                  htmlFor="description"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Description
                </label>
                <textarea
                  id="description"
                  name="description"
                  value={formData.description}
                  onChange={handleInputChange}
                  rows={4}
                  className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    errors.description ? "border-red-300" : "border-gray-300"
                  }`}
                  placeholder="Describe what this evidence seeker is for..."
                />
                {errors.description && (
                  <p className="mt-1 text-sm text-red-600">
                    {errors.description}
                  </p>
                )}
                <p className="mt-1 text-sm text-gray-500">
                  {formData.description.length}/500 characters
                </p>
              </div>

              <div>
                <label
                  htmlFor="language"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Primary language
                </label>
                <select
                  id="language"
                  name="language"
                  value={formData.language}
                  onChange={handleInputChange}
                  className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    errors.language ? "border-red-300" : "border-gray-300"
                  }`}
                >
                  {SUPPORTED_LANGUAGES.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                {errors.language && (
                  <p className="mt-1 text-sm text-red-600">{errors.language}</p>
                )}
                <p className="mt-1 text-sm text-gray-500">
                  Determines which language we pass to preprocessing.
                </p>
              </div>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="isPublic"
                  name="isPublic"
                  checked={formData.isPublic}
                  onChange={handleCheckboxChange}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <label
                  htmlFor="isPublic"
                  className="ml-2 block text-sm text-gray-900"
                >
                  Make this evidence seeker public
                </label>
              </div>
              <p className="text-sm text-gray-500 ml-6">
                Public evidence seekers can be viewed and tested by anyone, even
                without an account.
              </p>

              <div className="space-y-3 pt-4">
                <p className="text-sm font-medium text-gray-700">
                  Fact check publication
                </p>
                <p className="text-xs text-gray-500">
                  Choose whether successful runs auto-publish or stay unlisted until featured.
                </p>
                <div className="space-y-2">
                  <label className="flex items-start gap-2">
                    <input
                      type="radio"
                      name="factCheckPublicationMode"
                      value="AUTOPUBLISH"
                      checked={formData.factCheckPublicationMode === "AUTOPUBLISH"}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          factCheckPublicationMode: e.target.value,
                        }))
                      }
                      className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
                    />
                    <span>
                      <span className="text-sm font-medium text-gray-900">
                        Autopublish
                      </span>
                      <p className="text-xs text-gray-600">
                        Successful runs immediately appear on public pages.
                      </p>
                    </span>
                  </label>
                  <label className="flex items-start gap-2">
                    <input
                      type="radio"
                      name="factCheckPublicationMode"
                      value="MANUAL"
                      checked={formData.factCheckPublicationMode === "MANUAL"}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          factCheckPublicationMode: e.target.value,
                        }))
                      }
                      className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
                    />
                    <span>
                      <span className="text-sm font-medium text-gray-900">
                        Manual (unlisted)
                      </span>
                      <p className="text-xs text-gray-600">
                        Runs stay unlisted. Share links still work; admins feature chosen runs later.
                      </p>
                    </span>
                  </label>
                </div>
              </div>

              <div className="flex justify-end space-x-3 pt-4">
                <button
                  onClick={handleCancel}
                  className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 flex items-center space-x-2"
                >
                  <X className="h-4 w-4" />
                  <span>Cancel</span>
                </button>
                <button
                  onClick={handleSave}
                  disabled={loading}
                  className="btn-primary px-4 py-2 text-sm flex items-center space-x-2"
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      <span>Saving...</span>
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4" />
                      <span>Save Changes</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          ) : (
            // View Mode
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">
                    Title
                  </h4>
                  <p className="text-gray-900">{evidenceSeeker.title}</p>
                </div>

                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">
                    Visibility
                  </h4>
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      evidenceSeeker.isPublic
                        ? "bg-green-100 text-green-800"
                        : "bg-yellow-100 text-yellow-800"
                    }`}
                  >
                    {evidenceSeeker.isPublic ? "Public" : "Private"}
                  </span>
                </div>

                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">
                    Fact check publication
                  </h4>
                  <p className="text-gray-900">
                    {evidenceSeeker.factCheckPublicationMode === "MANUAL"
                      ? "Manual (unlisted until featured)"
                      : "Autopublish"}
                  </p>
                </div>

                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">
                    Language
                  </h4>
                  <p className="text-gray-900">
                    {getLanguageLabel(evidenceSeeker.language) ??
                      evidenceSeeker.language ??
                      "—"}
                  </p>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">
                  Description
                </h4>
                <p className="text-gray-900">
                  {evidenceSeeker.description || "No description provided."}
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4 border-t border-gray-200">
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-1">
                    Created
                  </h4>
                  <p className="text-sm text-gray-600">
                    {new Date(evidenceSeeker.createdAt).toLocaleDateString()}
                  </p>
                </div>

                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-1">
                    Last Updated
                  </h4>
                  <p className="text-sm text-gray-600">
                    {evidenceSeeker.updatedAt
                      ? new Date(evidenceSeeker.updatedAt).toLocaleDateString()
                      : "Never"}
                  </p>
                </div>

                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-1">
                    UUID
                  </h4>
                  <p className="text-sm text-gray-600 font-mono">
                    {evidenceSeeker.uuid}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EvidenceSeekerSettings;
