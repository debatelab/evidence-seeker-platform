import React, { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router";
import {
  EvidenceSeeker,
  EvidenceSeekerCreate,
  EvidenceSeekerUpdate,
} from "../../types/evidenceSeeker";
import {
  useEvidenceSeeker,
  useEvidenceSeekers,
} from "../../hooks/useEvidenceSeeker";

interface EvidenceSeekerFormProps {
  evidenceSeeker?: EvidenceSeeker;
  onSuccess?: () => void;
  onCancel?: () => void;
}

const EvidenceSeekerForm: React.FC<EvidenceSeekerFormProps> = ({
  evidenceSeeker,
  onSuccess,
  onCancel,
}) => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { evidenceSeeker: fetchedSeeker, loading: fetchLoading } =
    useEvidenceSeeker(parseInt(id || "0"));
  const { createEvidenceSeeker, updateEvidenceSeeker } = useEvidenceSeekers();

  // Use the prop if provided, otherwise use the fetched data
  const currentSeeker = evidenceSeeker || (id ? fetchedSeeker : null);
  const isEditMode = !!currentSeeker;

  const [formData, setFormData] = useState({
    title: currentSeeker?.title || "",
    description: currentSeeker?.description || "",
    isPublic: currentSeeker?.isPublic || false,
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Update form data when currentSeeker changes (for edit mode)
  useEffect(() => {
    if (currentSeeker) {
      setFormData({
        title: currentSeeker.title || "",
        description: currentSeeker.description || "",
        isPublic: currentSeeker.isPublic || false,
      });
    }
  }, [currentSeeker]);

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

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      let success = false;

      if (currentSeeker) {
        // Update existing
        const updateData: EvidenceSeekerUpdate = {
          title: formData.title,
          description: formData.description,
          isPublic: formData.isPublic,
        };
        success =
          (await updateEvidenceSeeker(currentSeeker.id, updateData)) || false;
      } else {
        // Create new
        const createData: EvidenceSeekerCreate = {
          title: formData.title,
          description: formData.description,
          isPublic: formData.isPublic,
        };
        success = (await createEvidenceSeeker(createData)) !== null;
      }

      if (success) {
        if (currentSeeker) {
          // For updates, navigate back to the list page with success message
          navigate("/evidence-seekers", {
            state: { message: "Evidence Seeker updated successfully!" },
          });
        } else {
          // For creation, navigate to the list page
          navigate("/evidence-seekers", {
            state: { message: "Evidence Seeker created successfully!" },
          });
        }
      }
    } catch (err) {
      setErrors({ general: "An error occurred. Please try again." });
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
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

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white shadow-sm rounded-lg border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            {isEditMode ? "Edit Evidence Seeker" : "Create Evidence Seeker"}
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {errors.general && (
            <div className="bg-red-50 border border-red-200 rounded-md p-4">
              <div className="text-red-800">{errors.general}</div>
            </div>
          )}

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
              <p className="mt-1 text-sm text-red-600">{errors.description}</p>
            )}
            <p className="mt-1 text-sm text-gray-500">
              {formData.description.length}/500 characters
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

          <div className="flex justify-end space-x-3 pt-4">
            {onCancel && (
              <button
                type="button"
                onClick={onCancel}
                className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Cancel
              </button>
            )}
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Saving..." : isEditMode ? "Update" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default EvidenceSeekerForm;
