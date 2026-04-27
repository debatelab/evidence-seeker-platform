import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { RegisterFormData } from "../../types/auth";

interface RegisterFormProps {
  _onSuccess?: () => void; // underscored: reserved for future use
  onSwitchToLogin?: () => void;
}

const RegisterForm: React.FC<RegisterFormProps> = ({
  _onSuccess: _onSuccess,
  onSwitchToLogin,
}) => {
  const { register, isLoading, error } = useAuth();
  const navigate = useNavigate();

  // Initialize form data from sessionStorage to preserve across remounts
  const [formData, setFormData] = useState<RegisterFormData>(() => {
    const saved = sessionStorage.getItem("registerFormData");
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        // Ignore invalid data
      }
    }
    return {
      email: "",
      username: "",
      password: "",
      confirmPassword: "",
    };
  });

  const [validationErrors, setValidationErrors] = useState<
    Partial<RegisterFormData>
  >({});

  // Save form data to sessionStorage whenever it changes
  useEffect(() => {
    sessionStorage.setItem("registerFormData", JSON.stringify(formData));
  }, [formData]);

  // Clear field-specific validation errors when that field changes
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));

    // Clear validation error for this specific field when user starts typing
    if (validationErrors[name as keyof RegisterFormData]) {
      setValidationErrors((prev) => ({
        ...prev,
        [name]: undefined,
      }));
    }
  };

  const validateForm = (): boolean => {
    const errors: Partial<RegisterFormData> = {};

    if (!formData.email) {
      errors.email = "Email is required";
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      errors.email = "Email is invalid";
    }

    if (!formData.username) {
      errors.username = "Username is required";
    } else if (formData.username.length < 3 || formData.username.length > 50) {
      errors.username = "Username must be between 3 and 50 characters";
    } else if (!/^[a-zA-Z0-9_-]+$/.test(formData.username)) {
      errors.username =
        "Username can only contain letters, numbers, underscores, and hyphens";
    }

    if (!formData.password) {
      errors.password = "Password is required";
    } else if (formData.password.length < 8) {
      errors.password = "Password must be at least 8 characters";
    } else if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(formData.password)) {
      errors.password =
        "Password must contain at least one lowercase letter, one uppercase letter, and one number";
    }

    if (!formData.confirmPassword) {
      errors.confirmPassword = "Please confirm your password";
    } else if (formData.password !== formData.confirmPassword) {
      errors.confirmPassword = "Passwords do not match";
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    const result = await register({
      email: formData.email,
      username: formData.username,
      password: formData.password,
    });

    if (result.success) {
      // Clear the form data and sessionStorage since registration was successful
      setFormData({
        email: "",
        username: "",
        password: "",
        confirmPassword: "",
      });
      sessionStorage.removeItem("registerFormData");

      // Redirect to email verification page
      navigate("/verify-email", {
        state: { email: formData.email, registrationSuccess: true },
      });
    } else {
      const registrationError = result.error;
      if (registrationError && registrationError.field !== "form") {
        setValidationErrors((prev) => ({
          ...prev,
          [registrationError.field]: registrationError.message,
        }));
      }
    }
  };

  return (
    <div className="w-full max-w-md mx-auto bg-white rounded-lg shadow-md p-6">
      <div className="mb-6">
        <h2 className="brand-title text-2xl text-center text-gray-800">
          Create Account
        </h2>
        <p className="text-center text-gray-600 mt-2">
          Join Evidence Seeker Platform
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
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
            value={formData.email}
            onChange={handleInputChange}
            className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary ${
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
            htmlFor="username"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Username
          </label>
          <input
            type="text"
            id="username"
            name="username"
            value={formData.username}
            onChange={handleInputChange}
            className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary ${
              validationErrors.username ? "border-red-500" : "border-gray-300"
            }`}
            placeholder="Choose a username"
            disabled={isLoading}
          />
          {validationErrors.username && (
            <p className="mt-1 text-sm text-red-600">
              {validationErrors.username}
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
            value={formData.password}
            onChange={handleInputChange}
            className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary ${
              validationErrors.password ? "border-red-500" : "border-gray-300"
            }`}
            placeholder="Create a password"
            disabled={isLoading}
          />
          {validationErrors.password && (
            <p className="mt-1 text-sm text-red-600">
              {validationErrors.password}
            </p>
          )}
        </div>

        <div>
          <label
            htmlFor="confirmPassword"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Confirm Password
          </label>
          <input
            type="password"
            id="confirmPassword"
            name="confirmPassword"
            value={formData.confirmPassword}
            onChange={handleInputChange}
            className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary ${
              validationErrors.confirmPassword
                ? "border-red-500"
                : "border-gray-300"
            }`}
            placeholder="Confirm your password"
            disabled={isLoading}
          />
          {validationErrors.confirmPassword && (
            <p className="mt-1 text-sm text-red-600">
              {validationErrors.confirmPassword}
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
          {isLoading ? "Creating Account..." : "Create Account"}
        </button>
      </form>

      <div className="mt-6 text-center">
        <p className="text-sm text-gray-600">
          Already have an account?{" "}
          <button
            type="button"
            onClick={onSwitchToLogin}
            className="text-primary hover:text-primary-hover font-medium focus:outline-none focus:underline"
            disabled={isLoading}
          >
            Sign in
          </button>
        </p>
      </div>
    </div>
  );
};

export default RegisterForm;
