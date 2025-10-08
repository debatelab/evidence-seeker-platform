/**
 * API Key Manager component for managing AI provider credentials
 */

import React, { useState } from "react";
import {
  Key,
  Plus,
  Edit,
  Trash2,
  Check,
  X,
  AlertTriangle,
  Loader2,
} from "lucide-react"; // removed Eye/EyeOff imports (unused)
import { useAPIKeys, useAPIKeyValidation } from "../../hooks/useConfig";
import { APIKeyRead, APIKeyCreate, APIKeyUpdate } from "../../types/config";

interface APIKeyManagerProps {
  evidenceSeekerUuid: string;
}

export const APIKeyManager: React.FC<APIKeyManagerProps> = ({
  evidenceSeekerUuid,
}) => {
  const {
    apiKeys,
    loading,
    error,
    createApiKey,
    updateApiKey,
    deleteApiKey,
    refetch: _refetch,
  } = useAPIKeys(evidenceSeekerUuid);

  const { validateApiKey, loading: validationLoading } = useAPIKeyValidation();

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingKey, setEditingKey] = useState<APIKeyRead | null>(null);
  // Removed unused visibleKeys state (visibility toggling not implemented)
  const [validationResults, setValidationResults] = useState<
    Record<number, { isValid: boolean; message: string }>
  >({});

  const [formData, setFormData] = useState<APIKeyCreate>({
    provider: "huggingface",
    name: "",
    api_key: "",
    description: "",
    expires_in_days: undefined,
  });

  const [editFormData, setEditFormData] = useState<APIKeyUpdate>({
    name: "",
    description: "",
    is_active: true,
  });

  const providers = [
    { value: "huggingface", label: "HuggingFace", prefix: "hf_" },
    { value: "openai", label: "OpenAI", prefix: "sk-" },
  ];

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createApiKey(formData);
      setShowCreateForm(false);
      setFormData({
        provider: "huggingface",
        name: "",
        api_key: "",
        description: "",
        expires_in_days: undefined,
      });
    } catch (error) {
      console.error("Failed to create API key:", error);
    }
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingKey) return;

    try {
      await updateApiKey(editingKey.id, editFormData);
      setEditingKey(null);
      setEditFormData({
        name: "",
        description: "",
        is_active: true,
      });
    } catch (error) {
      console.error("Failed to update API key:", error);
    }
  };

  const handleDelete = async (apiKeyId: number) => {
    if (!confirm("Are you sure you want to delete this API key?")) return;

    try {
      await deleteApiKey(apiKeyId);
    } catch (error) {
      console.error("Failed to delete API key:", error);
    }
  };

  // toggleKeyVisibility removed (feature not active)

  const validateKey = async (apiKey: APIKeyRead) => {
    try {
      const result = await validateApiKey({
        provider: apiKey.provider,
        api_key: apiKey.name, // This would need the actual key, but we don't store it
      });
      setValidationResults((prev) => ({
        ...prev,
        [apiKey.id]: {
          isValid: result.is_valid,
          message: result.message,
        },
      }));
    } catch (error) {
      console.error("Validation failed:", error);
    }
  };

  const startEdit = (apiKey: APIKeyRead) => {
    setEditingKey(apiKey);
    setEditFormData({
      name: apiKey.name,
      description: apiKey.description || "",
      is_active: apiKey.is_active,
    });
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const getStatusColor = (isActive: boolean, expiresAt?: string) => {
    if (!isActive) return "bg-gray-100 text-gray-800";
    if (expiresAt) {
      const expiryDate = new Date(expiresAt);
      const now = new Date();
      const daysUntilExpiry = Math.ceil(
        (expiryDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)
      );

      if (daysUntilExpiry < 0) return "bg-red-100 text-red-800";
      if (daysUntilExpiry < 7) return "bg-yellow-100 text-yellow-800";
    }
    return "bg-green-100 text-green-800";
  };

  const getStatusText = (isActive: boolean, expiresAt?: string) => {
    if (!isActive) return "Inactive";
    if (expiresAt) {
      const expiryDate = new Date(expiresAt);
      const now = new Date();
      const daysUntilExpiry = Math.ceil(
        (expiryDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)
      );

      if (daysUntilExpiry < 0) return "Expired";
      if (daysUntilExpiry < 7) return `Expires in ${daysUntilExpiry} days`;
    }
    return "Active";
  };

  if (loading && apiKeys.length === 0) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-2 text-gray-600">Loading API keys...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">
            API Key Management
          </h2>
          <p className="text-gray-600">
            Manage your AI provider credentials securely
          </p>
        </div>
        <button
          onClick={() => setShowCreateForm(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center space-x-2"
        >
          <Plus className="h-4 w-4" />
          <span>Add API Key</span>
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="h-5 w-5 text-red-600" />
            <span className="text-red-800">{error}</span>
          </div>
        </div>
      )}

      {/* Create Form */}
      {showCreateForm && (
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Add New API Key
          </h3>
          <form onSubmit={handleCreateSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Provider
                </label>
                <select
                  value={formData.provider}
                  onChange={(e) =>
                    setFormData({ ...formData, provider: e.target.value })
                  }
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                >
                  {providers.map((provider) => (
                    <option key={provider.value} value={provider.value}>
                      {provider.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="e.g., Production Key"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                API Key
              </label>
              <input
                type="password"
                value={formData.api_key}
                onChange={(e) =>
                  setFormData({ ...formData, api_key: e.target.value })
                }
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder={`e.g., ${providers.find((p) => p.value === formData.provider)?.prefix}...`}
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description (Optional)
              </label>
              <textarea
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                rows={3}
                placeholder="Optional description for this API key"
              />
            </div>

            <div className="flex items-center space-x-4">
              <button
                type="submit"
                disabled={loading}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-2"
              >
                {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                <span>Create API Key</span>
              </button>
              <button
                type="button"
                onClick={() => setShowCreateForm(false)}
                className="text-gray-600 hover:text-gray-800 px-4 py-2"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* API Keys List */}
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="p-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            Your API Keys ({apiKeys.length})
          </h3>
        </div>

        {apiKeys.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <Key className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No API keys configured yet.</p>
            <p className="text-sm mt-2">
              Add your first API key to enable AI-powered features.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {apiKeys.map((apiKey) => (
              <div key={apiKey.id} className="p-4">
                {editingKey?.id === apiKey.id ? (
                  // Edit Form
                  <form onSubmit={handleEditSubmit} className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Name
                        </label>
                        <input
                          type="text"
                          value={editFormData.name}
                          onChange={(e) =>
                            setEditFormData({
                              ...editFormData,
                              name: e.target.value,
                            })
                          }
                          className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          required
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Status
                        </label>
                        <select
                          value={editFormData.is_active ? "active" : "inactive"}
                          onChange={(e) =>
                            setEditFormData({
                              ...editFormData,
                              is_active: e.target.value === "active",
                            })
                          }
                          className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        >
                          <option value="active">Active</option>
                          <option value="inactive">Inactive</option>
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Description
                      </label>
                      <textarea
                        value={editFormData.description}
                        onChange={(e) =>
                          setEditFormData({
                            ...editFormData,
                            description: e.target.value,
                          })
                        }
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        rows={2}
                      />
                    </div>

                    <div className="flex items-center space-x-2">
                      <button
                        type="submit"
                        disabled={loading}
                        className="bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-1"
                      >
                        {loading && (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        )}
                        <span>Save</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingKey(null)}
                        className="text-gray-600 hover:text-gray-800 px-3 py-1"
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                ) : (
                  // Display Mode
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h4 className="font-medium text-gray-900">
                          {apiKey.name}
                        </h4>
                        <span
                          className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(
                            apiKey.is_active,
                            apiKey.expires_at
                          )}`}
                        >
                          {getStatusText(apiKey.is_active, apiKey.expires_at)}
                        </span>
                        <span className="text-sm text-gray-500 capitalize">
                          {apiKey.provider}
                        </span>
                      </div>

                      {apiKey.description && (
                        <p className="text-sm text-gray-600 mb-2">
                          {apiKey.description}
                        </p>
                      )}

                      <div className="flex items-center space-x-4 text-xs text-gray-500">
                        <span>Created: {formatDate(apiKey.created_at)}</span>
                        {apiKey.last_used_at && (
                          <span>
                            Last used: {formatDate(apiKey.last_used_at)}
                          </span>
                        )}
                        {apiKey.expires_at && (
                          <span>Expires: {formatDate(apiKey.expires_at)}</span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => validateKey(apiKey)}
                        disabled={validationLoading}
                        className="text-blue-600 hover:text-blue-800 p-1"
                        title="Validate API Key"
                      >
                        {validationResults[apiKey.id] ? (
                          validationResults[apiKey.id].isValid ? (
                            <Check className="h-4 w-4" />
                          ) : (
                            <X className="h-4 w-4" />
                          )
                        ) : (
                          <Key className="h-4 w-4" />
                        )}
                      </button>

                      <button
                        onClick={() => startEdit(apiKey)}
                        className="text-gray-600 hover:text-gray-800 p-1"
                        title="Edit API Key"
                      >
                        <Edit className="h-4 w-4" />
                      </button>

                      <button
                        onClick={() => handleDelete(apiKey.id)}
                        className="text-red-600 hover:text-red-800 p-1"
                        title="Delete API Key"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                )}

                {/* Validation Result */}
                {validationResults[apiKey.id] && (
                  <div className="mt-2 text-sm">
                    {validationResults[apiKey.id].isValid ? (
                      <span className="text-green-600 flex items-center space-x-1">
                        <Check className="h-3 w-3" />
                        <span>{validationResults[apiKey.id].message}</span>
                      </span>
                    ) : (
                      <span className="text-red-600 flex items-center space-x-1">
                        <X className="h-3 w-3" />
                        <span>{validationResults[apiKey.id].message}</span>
                      </span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
