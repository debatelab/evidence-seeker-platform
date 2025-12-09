import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { LoginFormData } from "../../types/auth";

interface LoginFormProps {
  onSuccess?: () => void;
  onSwitchToRegister?: () => void;
}

const LoginForm: React.FC<LoginFormProps> = ({
  onSuccess,
  onSwitchToRegister,
}) => {
  const { login, isLoading, error, clearError } = useAuth();
  const [formData, setFormData] = useState<LoginFormData>({
    email: "",
    password: "",
  });
  const emailRef = useRef<HTMLInputElement | null>(null);
  const passwordRef = useRef<HTMLInputElement | null>(null);
  const [validationErrors, setValidationErrors] = useState<
    Partial<LoginFormData>
  >({});

  const resetErrors = useCallback(() => {
    setValidationErrors((prev) => (Object.keys(prev).length ? {} : prev));
    if (error) {
      clearError();
    }
  }, [clearError, error]);

  // Some password managers (e.g., 1Password) can populate fields without firing React's onChange.
  // Sync the DOM values back into state whenever inputs change or autofill kicks in.
  useEffect(() => {
    const syncFromDom = () => {
      const emailValue = emailRef.current?.value ?? "";
      const passwordValue = passwordRef.current?.value ?? "";
      setFormData((prev) => {
        if (prev.email === emailValue && prev.password === passwordValue) {
          return prev;
        }
        resetErrors();
        return { email: emailValue, password: passwordValue };
      });
    };

    const emailEl = emailRef.current;
    const passwordEl = passwordRef.current;
    const events: Array<keyof HTMLElementEventMap> = ["input", "change"];

    events.forEach((event) => {
      emailEl?.addEventListener(event, syncFromDom);
      passwordEl?.addEventListener(event, syncFromDom);
    });

    // Kick off a sync shortly after mount to capture any immediate autofill
    const timer = window.setTimeout(syncFromDom, 100);

    return () => {
      events.forEach((event) => {
        emailEl?.removeEventListener(event, syncFromDom);
        passwordEl?.removeEventListener(event, syncFromDom);
      });
      window.clearTimeout(timer);
    };
  }, [resetErrors]);

  const validateForm = (): boolean => {
    const errors: Partial<LoginFormData> = {};

    if (!formData.email) {
      errors.email = "Email is required";
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      errors.email = "Email is invalid";
    }

    if (!formData.password) {
      errors.password = "Password is required";
    } else if (formData.password.length < 6) {
      errors.password = "Password must be at least 6 characters";
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    resetErrors();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    const result = await login(formData);

    if (result.success) {
      onSuccess?.();
    }
  };

  return (
    <div className="w-full max-w-md mx-auto bg-white rounded-lg shadow-md p-6">
      <div className="mb-6">
        <h2 className="brand-title text-2xl text-center text-gray-800">
          Sign In
        </h2>
        <p className="text-center text-gray-600 mt-2">
          Welcome back to Evidence Seeker
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="space-y-4"
        autoComplete="on"
      >
        <div>
          <label
            htmlFor="email"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Email Address
          </label>
          <input
            type="email"
            id="email"
            name="email"
            ref={emailRef}
            value={formData.email}
            onChange={handleInputChange}
            autoComplete="username"
            className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              validationErrors.email ? "border-red-500" : "border-gray-300"
            }`}
            placeholder="Enter your email"
            disabled={isLoading}
          />
          {validationErrors.email && (
            <p className="mt-1 text-sm text-red-600">
              {validationErrors.email}
            </p>
          )}
        </div>

        <div>
          <label
            htmlFor="password"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Password
          </label>
          <input
            type="password"
            id="password"
            name="password"
            ref={passwordRef}
            value={formData.password}
            onChange={handleInputChange}
            autoComplete="current-password"
            className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary ${
              validationErrors.password ? "border-red-500" : "border-gray-300"
            }`}
            placeholder="Enter your password"
            disabled={isLoading}
          />
          {validationErrors.password && (
            <p className="mt-1 text-sm text-red-600">
              {validationErrors.password}
            </p>
          )}
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-3">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        <button
          type="submit"
          disabled={isLoading}
          className="btn-primary w-full"
        >
          {isLoading ? "Signing In..." : "Sign In"}
        </button>
      </form>

      <div className="mt-4 text-center">
        <Link
          to="/forgot-password"
          className="text-sm text-primary hover:text-primary-hover focus:outline-none focus:underline"
        >
          Forgot your password?
        </Link>
      </div>

      <div className="mt-6 text-center">
        <p className="text-sm text-gray-600">
          Don't have an account?{" "}
          <button
            type="button"
            onClick={onSwitchToRegister}
            className="text-primary hover:text-primary-hover font-medium focus:outline-none focus:underline"
            disabled={isLoading}
          >
            Sign up
          </button>
        </p>
      </div>
    </div>
  );
};

export default LoginForm;
