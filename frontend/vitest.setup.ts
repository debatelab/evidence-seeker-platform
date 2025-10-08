// Global test setup for Vitest
// Ensure Vitest's expect is initialized before extending with jest-dom matchers.
import { expect } from "vitest";
// Attach expect explicitly to globalThis (sometimes needed in ESM + setupFiles ordering)
// so that jest-dom can patch it.
(globalThis as any).expect = expect;
import "@testing-library/jest-dom";
