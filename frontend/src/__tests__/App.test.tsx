import { beforeEach, afterEach, test, expect } from "vitest";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import App from "../App";
import { AuthProvider } from "../context/AuthContext";

// Mock localStorage token and user before rendering
beforeEach(() => {
  localStorage.setItem("access_token", "dummy-token");
  localStorage.setItem(
    "user",
    JSON.stringify({
      id: 1,
      email: "test@example.com",
      is_active: true,
      is_verified: true,
      is_superuser: true,
    })
  );
});

afterEach(() => {
  localStorage.clear();
});

test("renders welcome page immediately after login state is present", async () => {
  render(
    <AuthProvider>
      <App />
    </AuthProvider>
  );

  // Wait for the welcome message to appear
  expect(
    await screen.findByText(/Welcome, test@example.com/i)
  ).toBeInTheDocument();
});
