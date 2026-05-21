import { expect, test } from "@playwright/test";

// Widget is served at localhost:5173 by `npm run dev`.
// API must be running at localhost:8000 with demo fallback enabled.
// Widget URL: http://localhost:5173?widget_id=demo-widget&api_base_url=http://localhost:8000

const WIDGET_URL = "/?widget_id=demo-widget&api_base_url=http%3A%2F%2Flocalhost%3A8000";

test.describe("Maintainer's Copilot Widget", () => {

  test("shows chat bubble on load", async ({ page }) => {
    await page.goto(WIDGET_URL);
    const bubble = page.locator(".mcw-bubble");
    await expect(bubble).toBeVisible();
    await expect(bubble).toHaveAttribute("aria-label", "Open Maintainer's Copilot");
  });

  test("opens panel when bubble is clicked", async ({ page }) => {
    await page.goto(WIDGET_URL);
    await page.click(".mcw-bubble");
    await expect(page.locator(".mcw-panel")).toBeVisible();
    await expect(page.locator(".mcw-header-name")).toContainText("Maintainer's Copilot");
  });

  test("shows empty state with greeting and suggested prompts", async ({ page }) => {
    await page.goto(WIDGET_URL);
    await page.click(".mcw-bubble");
    await expect(page.locator(".mcw-empty-greeting")).toBeVisible();
    const prompts = page.locator(".mcw-suggestion");
    await expect(prompts).toHaveCount(4);
  });

  test("clicking a suggested prompt fills the input", async ({ page }) => {
    await page.goto(WIDGET_URL);
    await page.click(".mcw-bubble");
    const firstPrompt = page.locator(".mcw-suggestion").first();
    const promptText = await firstPrompt.textContent();
    await firstPrompt.click();
    await expect(page.locator("textarea")).toHaveValue(promptText!);
  });

  test("sends a message and receives streaming response", async ({ page }) => {
    await page.goto(WIDGET_URL);
    await page.click(".mcw-bubble");
    await page.fill("textarea", "How do I debug a memory leak?");
    await page.click(".mcw-send-btn");

    // User bubble appears
    await expect(page.locator(".mcw-row-user .mcw-msg-bubble p")).toContainText("How do I debug a memory leak?");

    // Wait for assistant response (streaming done)
    await expect(page.locator(".mcw-row-asst .mcw-msg-bubble p")).not.toBeEmpty({ timeout: 15_000 });
  });

  test("shows tool badge on assistant response", async ({ page }) => {
    await page.goto(WIDGET_URL);
    await page.click(".mcw-bubble");
    await page.fill("textarea", "How do I debug a memory leak?");
    await page.click(".mcw-send-btn");

    await expect(page.locator(".mcw-row-asst .mcw-msg-bubble p")).not.toBeEmpty({ timeout: 15_000 });
    await expect(page.locator(".mcw-tool-badge")).toBeVisible();
  });

  test("closes panel via close button", async ({ page }) => {
    await page.goto(WIDGET_URL);
    await page.click(".mcw-bubble");
    await expect(page.locator(".mcw-panel")).toBeVisible();
    await page.click(".mcw-hdr-close");
    await expect(page.locator(".mcw-panel")).not.toBeVisible();
    await expect(page.locator(".mcw-bubble")).toBeVisible();
  });

  test("issue context panel toggles open and closed", async ({ page }) => {
    await page.goto(WIDGET_URL);
    await page.click(".mcw-bubble");
    await expect(page.locator(".mcw-context-panel")).not.toBeVisible();
    await page.click(".mcw-ctx-toggle");
    await expect(page.locator(".mcw-context-panel")).toBeVisible();
    await page.click(".mcw-ctx-toggle");
    await expect(page.locator(".mcw-context-panel")).not.toBeVisible();
  });

  test("shows classify tool card when classifying", async ({ page }) => {
    await page.goto(WIDGET_URL);
    await page.click(".mcw-bubble");

    // Use issue context to provide content
    await page.click(".mcw-ctx-toggle");
    await page.fill(".mcw-context-input", "Memory leak in https.request");
    await page.fill(".mcw-context-textarea", "Repeated requests increase memory. Version v18.0.0");
    await page.fill("textarea", "Classify this issue");
    await page.click(".mcw-send-btn");

    // Wait for response
    await expect(page.locator(".mcw-row-asst .mcw-msg-bubble")).not.toBeEmpty({ timeout: 15_000 });
  });

  test("clear conversation button removes messages", async ({ page }) => {
    await page.goto(WIDGET_URL);
    await page.click(".mcw-bubble");
    await page.fill("textarea", "hello");
    await page.click(".mcw-send-btn");
    await expect(page.locator(".mcw-row-user")).toBeVisible();

    // Wait for response then clear
    await expect(page.locator(".mcw-row-asst .mcw-msg-bubble p")).not.toBeEmpty({ timeout: 15_000 });
    await page.click('[aria-label="Clear conversation"]');
    await expect(page.locator(".mcw-row-user")).not.toBeVisible();
    await expect(page.locator(".mcw-empty")).toBeVisible();
  });

  test("send button disabled when input is empty", async ({ page }) => {
    await page.goto(WIDGET_URL);
    await page.click(".mcw-bubble");
    await expect(page.locator(".mcw-send-btn")).toBeDisabled();
    await page.fill("textarea", "test");
    await expect(page.locator(".mcw-send-btn")).not.toBeDisabled();
  });

  test("send button shows spinner while streaming", async ({ page }) => {
    await page.goto(WIDGET_URL);
    await page.click(".mcw-bubble");
    await page.fill("textarea", "How does Node.js handle async I/O?");
    await page.click(".mcw-send-btn");
    await expect(page.locator(".mcw-send-spinner")).toBeVisible();
    // Spinner disappears when done
    await expect(page.locator(".mcw-send-spinner")).not.toBeVisible({ timeout: 15_000 });
  });
});
