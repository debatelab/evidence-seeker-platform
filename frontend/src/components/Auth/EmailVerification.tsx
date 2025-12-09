import React, { useState, useEffect, useCallback } from "react";
import { useNavigate, useSearchParams, useLocation } from "react-router-dom";
import { AlertTriangle, CheckCircle, Loader2 } from "lucide-react";

interface EmailVerificationProps {
  email?: string;
  _onVerificationComplete?: () => void; // underscored: reserved for future use
  _onResendEmail?: () => void; // underscored: reserved for future use
  showResendOption?: boolean;
}

const EmailVerification: React.FC<EmailVerificationProps> = ({
  email: propEmail,
  _onVerificationComplete: _onVerificationComplete,
  _onResendEmail: _onResendEmail,
  showResendOption = false,
}) => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const locationState = (location.state as
    | { email?: string; registrationSuccess?: boolean }
    | null) ?? { email: undefined, registrationSuccess: false };
  const [isVerifying, setIsVerifying] = useState(false);
  const [isVerified, setIsVerified] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isResending, setIsResending] = useState(false);
  const [resendMessage, setResendMessage] = useState<string | null>(null);

  const token = searchParams.get("token");
  const locationEmail = locationState.email;
  const registrationSuccess = locationState.registrationSuccess;
  const displayEmail = propEmail || locationEmail;

  const verifyEmail = useCallback(
    async (verificationToken: string) => {
      setIsVerifying(true);
      setError(null);

      try {
        const response = await fetch("/api/v1/auth/verify", {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: new URLSearchParams({
            token: verificationToken,
          }),
        });

        if (response.ok) {
          setIsVerified(true);
          setTimeout(() => {
            navigate("/dashboard");
          }, 2000);
        } else {
          const errorData = await response.json();
          setError(
            errorData.detail ||
              "Verification failed. The link may be expired or invalid."
          );
        }
      } catch (err) {
        setError("Network error. Please try again.");
      } finally {
        setIsVerifying(false);
      }
    },
    [navigate]
  );

  useEffect(() => {
    if (token && !isVerified) {
      verifyEmail(token);
    }
  }, [token, isVerified, verifyEmail]);

  const handleResendVerification = async () => {
    setIsResending(true);
    setResendMessage(null);
    setError(null);

    try {
      const response = await fetch("/api/v1/auth/resend-verification", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });

      if (response.ok) {
        setResendMessage(
          "Verification email sent successfully! Please check your inbox."
        );
      } else {
        const errorData = await response.json();
        setError(errorData.detail || "Failed to resend verification email.");
      }
    } catch (err) {
      setError("Network error. Please try again.");
    } finally {
      setIsResending(false);
    }
  };

  if (isVerified) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-8">
          <div className="text-center">
            <CheckCircle className="mx-auto h-16 w-16 text-green-500" />
            <h2 className="brand-title mt-6 text-3xl text-gray-900">
              Email Verified!
            </h2>
            <p className="mt-2 text-sm text-gray-600">
              Your email has been successfully verified. You can now access all
              features of the platform.
            </p>
            <p className="mt-4 text-sm text-gray-500">
              Redirecting to dashboard...
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <div className="mx-auto h-16 w-16 rounded-full flex items-center justify-center bg-primary-soft">
            <AlertTriangle className="h-8 w-8 text-primary" />
          </div>
          <h2 className="brand-title mt-6 text-3xl text-gray-900">
            Verify Your Email
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            {displayEmail ? (
              <>
                We&apos;ve sent a verification link to{" "}
                <strong>{displayEmail}</strong>
              </>
            ) : (
              "We've sent a verification link to your email address"
            )}
          </p>
        </div>

        {registrationSuccess && (
          <div className="bg-green-50 border border-green-200 rounded-md p-4">
            <div className="flex">
              <CheckCircle className="h-5 w-5 text-green-500" />
              <div className="ml-3">
                <p className="text-sm font-medium text-green-800">
                  Account created
                </p>
                <p className="mt-1 text-sm text-green-700">
                  We&apos;ve sent a verification link to{" "}
                  {displayEmail ?? "your email"}. Please confirm it to finish
                  setting up your account.
                </p>
              </div>
            </div>
          </div>
        )}

        {isVerifying && (
          <div className="bg-primary-soft border border-primary-border rounded-md p-4">
            <div className="flex">
              <Loader2 className="h-5 w-5 text-primary animate-spin" />
              <div className="ml-3">
                <p className="text-sm font-medium text-primary-strong">
                  Verifying your email...
                </p>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <AlertTriangle className="h-5 w-5 text-red-400" />
              <div className="ml-3">
                <p className="text-sm font-medium text-red-800">
                  Verification Failed
                </p>
                <p className="mt-1 text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}

        {resendMessage && (
          <div className="bg-green-50 border border-green-200 rounded-md p-4">
            <div className="flex">
              <CheckCircle className="h-5 w-5 text-green-400" />
              <div className="ml-3">
                <p className="text-sm font-medium text-green-800">
                  {resendMessage}
                </p>
              </div>
            </div>
          </div>
        )}

        {(showResendOption || !token) && (
          <div className="text-center">
            <p className="text-sm text-gray-600 mb-4">
              Didn&apos;t receive the email? Check your spam folder or request a
              new one.
            </p>
            <button
              onClick={handleResendVerification}
              disabled={isResending}
              className="btn-primary w-full flex justify-center text-sm"
            >
              {isResending ? (
                <>
                  <Loader2 className="animate-spin -ml-1 mr-3 h-5 w-5" />
                  Sending...
                </>
              ) : (
                "Resend Verification Email"
              )}
            </button>
          </div>
        )}

        <div className="text-center">
          <button
            onClick={() => navigate("/login")}
            className="text-sm text-primary hover:text-primary-hover"
          >
            Back to Login
          </button>
        </div>
      </div>
    </div>
  );
};

export default EmailVerification;
