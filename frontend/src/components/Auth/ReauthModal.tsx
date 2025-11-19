import React, { useEffect, useState } from "react";
import { useAuth } from "../../hooks/useAuth";

const ReauthModal: React.FC = () => {
  const { reauthModalOpen, dismissReauthPrompt, login, logout, user } =
    useAuth();
  const [email, setEmail] = useState(user?.email ?? "");
  const [password, setPassword] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setEmail(user?.email ?? "");
  }, [user?.email]);

  useEffect(() => {
    if (!reauthModalOpen) {
      setPassword("");
      setLocalError(null);
      setSubmitting(false);
    }
  }, [reauthModalOpen]);

  if (!reauthModalOpen) {
    return null;
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!email || !password) {
      setLocalError("Email and password are required.");
      return;
    }
    setSubmitting(true);
    setLocalError(null);
    const result = await login({ email, password });
    if (!result.success) {
      setLocalError(result.error ?? "Failed to re-authenticate. Try again.");
      setSubmitting(false);
    } else {
      setSubmitting(false);
      setPassword("");
    }
  };

  const handleLogout = async () => {
    await logout();
    dismissReauthPrompt();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/60 px-4">
      <div className="w-full max-w-md rounded-lg bg-white shadow-xl">
        <div className="border-b border-gray-200 px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-900">
            Session expired
          </h3>
          <p className="text-sm text-gray-600">
            Please sign in again to keep working on your setup.
          </p>
        </div>
        <form className="space-y-4 px-6 py-6" onSubmit={handleSubmit}>
          <div>
            <label
              htmlFor="reauth-email"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Email
            </label>
            <input
              id="reauth-email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary"
            />
          </div>
          <div>
            <label
              htmlFor="reauth-password"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Password
            </label>
            <input
              id="reauth-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter your password"
            />
          </div>
          {localError && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {localError}
            </div>
          )}
          <div className="flex flex-col gap-3 pt-2 sm:flex-row sm:justify-between">
            <button
              type="button"
              onClick={handleLogout}
              className="text-sm font-medium text-gray-600 hover:text-gray-900 underline"
              disabled={submitting}
            >
              Sign out instead
            </button>
            <button
              type="submit"
              className="btn-primary px-4 py-2 text-sm"
              disabled={submitting}
            >
              {submitting ? "Signing in..." : "Sign back in"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ReauthModal;
