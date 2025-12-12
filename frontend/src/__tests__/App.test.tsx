import { beforeEach, afterEach, test, expect, vi } from "vitest";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import App from "../App";
import { AuthProvider } from "../context/AuthContext";
import api from "../utils/api";
import { EvidenceSeeker } from "../types/evidenceSeeker";

const mockEvidenceSeekers: EvidenceSeeker[] = [
  {
    id: 1,
    uuid: "mock-uuid",
    title: "Demo Evidence Seeker",
    description: "A demo seeker for testing.",
    language: "en",
    logoUrl: null,
    isPublic: true,
    factCheckPublicationMode: "MANUAL",
    publishedAt: null,
    createdBy: 1,
    createdAt: "2024-01-01T00:00:00.000Z",
    updatedAt: "2024-01-01T00:00:00.000Z",
    configurationState: "READY",
    missingRequirements: [],
    setupMode: "SIMPLE",
    documentSkipAcknowledged: false,
  },
];

// Mock localStorage token and user before rendering
beforeEach(() => {
  vi.restoreAllMocks();

  vi.spyOn(api, "get").mockResolvedValue({ data: mockEvidenceSeekers });
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
      username: "test-user",
      isActive: true,
      isVerified: true,
      isSuperuser: true,
      permissions: [],
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

  // Wait for the dashboard to load the evidence seekers list
  expect(
    await screen.findByText(mockEvidenceSeekers[0].title)
  ).toBeInTheDocument();

  // Ensure the logged in user's email is displayed in the account info section
  expect(
    await screen.findByText(/Welcome,\s*test@example.com/i)
  ).toBeInTheDocument();
});
