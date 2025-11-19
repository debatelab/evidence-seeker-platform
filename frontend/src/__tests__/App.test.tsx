import { beforeEach, afterEach, test, expect, vi } from "vitest";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import App from "../App";
import { AuthProvider } from "../context/AuthContext";

// Mock localStorage token and user before rendering
beforeEach(() => {
  vi.restoreAllMocks();
  class MockRequest {
    input: RequestInfo | URL;
    init: RequestInit;
    method: string;
    headers: HeadersInit | undefined;
    body: BodyInit | null | undefined;
    signal: AbortSignal | undefined;
    url: string;

    constructor(input: RequestInfo | URL, init: RequestInit = {}) {
      this.input = input;
      this.init = init;
      this.method = init.method ?? "GET";
      this.headers = init.headers;
      this.body = init.body;
      this.signal = init.signal ?? undefined;
      this.url =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.toString()
            : (input.url ?? "");
    }

    clone(): MockRequest {
      return new MockRequest(this.input, { ...this.init });
    }
  }

  vi.stubGlobal("Request", MockRequest);
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve(
        new Response(JSON.stringify({}), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
    )
  );
  window.history.pushState({}, "", "/app");
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
  vi.unstubAllGlobals();
});

test("renders welcome page immediately after login state is present", async () => {
  render(
    <AuthProvider>
      <App />
    </AuthProvider>
  );

  // Wait for the dashboard welcome heading to appear
  expect(
    await screen.findByText(/Welcome to the Evidence Seeker Platform/i)
  ).toBeInTheDocument();

  // Ensure the logged in user's email is displayed in the account info section
  expect(await screen.findByText("test@example.com")).toBeInTheDocument();
});
