import React from "react";

interface AccessDeniedMessageProps {
  message?: string;
  showRequestAccess?: boolean;
  onRequestAccess?: () => void;
}

export const AccessDeniedMessage: React.FC<AccessDeniedMessageProps> = ({
  message = "You don't have permission to access this resource.",
  showRequestAccess = false,
  onRequestAccess,
}) => {
  return (
    <div className="bg-red-50 border border-red-200 rounded-md p-4">
      <div className="flex">
        <div className="flex-shrink-0">
          <svg
            className="h-5 w-5 text-red-400"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <div className="ml-3">
          <h3 className="text-sm font-medium text-red-800">Access Denied</h3>
          <div className="mt-2 text-sm text-red-700">
            <p>{message}</p>
          </div>
          {showRequestAccess && onRequestAccess && (
            <div className="mt-4">
              <div className="-mx-2 -my-1.5 flex">
                <button
                  type="button"
                  onClick={onRequestAccess}
                  className="bg-red-50 px-2 py-1.5 rounded-md text-sm font-medium text-red-800 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-red-50 focus:ring-red-600"
                >
                  Request Access
                </button>
              </div>
            </div>
          )}
          <div className="mt-4 text-sm text-red-600">
            <p>
              If you believe this is an error, please contact your
              administrator.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
