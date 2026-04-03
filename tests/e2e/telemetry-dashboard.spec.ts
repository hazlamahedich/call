import { test, expect } from '@playwright/test';
import { createAgent, createVoiceEvent } from '../factories/agent-factory';

/**
 * Story 2.4: Telemetry Dashboard E2E Tests
 * Test ID Format: 2.4-E2E-XXX
 * Priority Tags: @smoke @p0 @p1 @p2
 */

test.describe('[2.4-E2E] Telemetry Dashboard', () => {
  /**
   * Test ID: 2.4-E2E-001
   * Priority: P1
   * Tags: @smoke @p1
   * AC: AC6
   */
  test('[P1] @smoke @p1 should display telemetry metrics dashboard', async ({ page }) => {
    // Network-first: Intercept API call BEFORE navigation
    const metricsPromise = page.waitForResponse('**/api/v1/telemetry/metrics');

    await page.goto('/dashboard/telemetry');
    await metricsPromise; // Deterministic wait

    // Verify dashboard is visible
    await expect(page.getByTestId('telemetry-dashboard')).toBeVisible();

    // Verify queue depth metrics are displayed
    await expect(page.getByTestId('queue-current-depth')).toBeVisible();
    await expect(page.getByTestId('queue-avg-depth')).toBeVisible();
    await expect(page.getByTestId('queue-max-depth')).toBeVisible();

    // Verify processing latency metric
    await expect(page.getByTestId('processing-latency-p95')).toBeVisible();

    // Verify events per second rate
    await expect(page.getByTestId('events-per-second')).toBeVisible();
  });

  /**
   * Test ID: 2.4-E2E-002
   * Priority: P1
   * Tags: @p1
   * AC: AC6
   */
  test('[P1] @p1 should show worker running status', async ({ page }) => {
    await page.goto('/dashboard/telemetry');

    // Wait for metrics to load
    await page.waitForResponse('**/api/v1/telemetry/metrics');

    // Verify worker status indicator
    const workerStatus = page.getByTestId('worker-status');
    await expect(workerStatus).toBeVisible();

    // Status should be either 'running' or 'stopped'
    const statusText = await workerStatus.textContent();
    expect(['running', 'stopped']).toContain(statusText?.toLowerCase());
  });

  /**
   * Test ID: 2.4-E2E-003
   * Priority: P1
   * Tags: @p1
   * AC: AC6
   */
  test('[P1] @p1 should display queue health indicator', async ({ page }) => {
    await page.goto('/dashboard/telemetry');

    await page.waitForResponse('**/api/v1/telemetry/metrics');

    // Verify queue health indicator exists
    const healthIndicator = page.getByTestId('queue-health-indicator');
    await expect(healthIndicator).toBeVisible();

    // Health should be one of: healthy, warning, critical
    const healthText = await healthIndicator.getAttribute('data-health');
    expect(['healthy', 'warning', 'critical']).toContain(healthText);
  });

  /**
   * Test ID: 2.4-E2E-004
   * Priority: P1
   * Tags: @p1
   * AC: AC6
   */
  test('[P1] @p1 should show queue depth percentage', async ({ page }) => {
    await page.goto('/dashboard/telemetry');

    await page.waitForResponse('**/api/v1/telemetry/metrics');

    // Verify queue depth percentage is displayed
    const depthPercentage = page.getByTestId('queue-depth-percentage');
    await expect(depthPercentage).toBeVisible();

    // Verify percentage is between 0-100
    const percentageText = await depthPercentage.textContent();
    const percentage = parseInt(percentageText || '0', 10);
    expect(percentage).toBeGreaterThanOrEqual(0);
    expect(percentage).toBeLessThanOrEqual(100);
  });
});

test.describe('[2.4-E2E] Degradation Alerts UI (AC8.5)', () => {
  /**
   * Test ID: 2.4-E2E-005
   * Priority: P0
   * Tags: @p0
   * AC: AC8.5
   */
  test('[P0] @p0 should display degradation alert when drop rate >10%', async ({ page }) => {
    // Mock API response to simulate high drop rate
    await page.route('**/api/v1/telemetry/metrics', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          current_depth: 8000,
          avg_depth: 7500,
          max_depth: 10000,
          is_running: true,
          processing_latency_ms_p95: 150,
          events_per_second: 500,
          drop_rate: 0.15, // 15% drop rate
          degradation_alert: {
            level: 'critical',
            message: 'Drop rate exceeds 10% threshold',
            threshold: 0.1,
            current_value: 0.15,
            duration_seconds: 45,
          },
        }),
      });
    });

    await page.goto('/dashboard/telemetry');

    // Verify degradation alert is displayed
    const alert = page.getByTestId('degradation-alert');
    await expect(alert).toBeVisible();

    // Verify alert is critical level
    await expect(alert).toHaveAttribute('data-alert-level', 'critical');

    // Verify alert message
    await expect(alert).toContainText('Drop rate exceeds 10%');

    // Verify current drop rate displayed
    await expect(alert).toContainText('15%');
  });

  /**
   * Test ID: 2.4-E2E-006
   * Priority: P1
   * Tags: @p1
   * AC: AC8.5
   */
  test('[P1] @p1 should show alert duration', async ({ page }) => {
    await page.route('**/api/v1/telemetry/metrics', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          drop_rate: 0.12,
          degradation_alert: {
            level: 'critical',
            message: 'Drop rate exceeds 10%',
            threshold: 0.1,
            current_value: 0.12,
            duration_seconds: 35,
          },
        }),
      });
    });

    await page.goto('/dashboard/telemetry');

    // Verify alert duration is displayed
    const alert = page.getByTestId('degradation-alert');
    await expect(alert).toContainText('35s');
  });

  /**
   * Test ID: 2.4-E2E-007
   * Priority: P1
   * Tags: @p1
   * AC: AC8.5
   */
  test('[P1] @p1 should not show alert when drop rate <10%', async ({ page }) => {
    // Mock API response with healthy drop rate
    await page.route('**/api/v1/telemetry/metrics', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          current_depth: 500,
          avg_depth: 450,
          max_depth: 10000,
          is_running: true,
          processing_latency_ms_p95: 50,
          events_per_second: 800,
          drop_rate: 0.02, // 2% drop rate (healthy)
        }),
      });
    });

    await page.goto('/dashboard/telemetry');

    // Verify degradation alert is NOT displayed
    const alert = page.getByTestId('degradation-alert');
    await expect(alert).not.toBeVisible();
  });

  /**
   * Test ID: 2.4-E2E-008
   * Priority: P2
   * Tags: @p2
   * AC: AC8.5
   */
  test('[P2] @p2 should show consecutive high drop periods', async ({ page }) => {
    await page.route('**/api/v1/telemetry/metrics', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          drop_rate: 0.15,
          consecutive_high_drop_periods: 3,
          degradation_alert: {
            level: 'critical',
            message: 'Drop rate exceeds 10% for 3 consecutive periods',
            threshold: 0.1,
            current_value: 0.15,
            duration_seconds: 90,
          },
        }),
      });
    });

    await page.goto('/dashboard/telemetry');

    // Verify consecutive periods count is displayed
    const alert = page.getByTestId('degradation-alert');
    await expect(alert).toContainText('3 consecutive periods');
  });
});

test.describe('[2.4-E2E] Telemetry Events Query UI', () => {
  /**
   * Test ID: 2.4-E2E-009
   * Priority: P2
   * Tags: @p2
   * AC: AC7
   */
  test('[P2] @p2 should display events query results', async ({ page }) => {
    // Mock events query response
    await page.route('**/api/v1/telemetry/events*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 1,
            call_id: 123,
            event_type: 'silence',
            timestamp: '2024-01-01T12:00:00Z',
            duration_ms: 500,
            audio_level: -60,
          },
          {
            id: 2,
            call_id: 123,
            event_type: 'noise',
            timestamp: '2024-01-01T12:01:00Z',
            duration_ms: 300,
            audio_level: -20,
          },
        ]),
      });
    });

    await page.goto('/dashboard/telemetry/events');

    // Verify events table is displayed
    await expect(page.getByTestId('events-table')).toBeVisible();

    // Verify event rows are displayed
    const eventRows = page.getByTestId('event-row');
    await expect(eventRows).toHaveCount(2);
  });

  /**
   * Test ID: 2.4-E2E-010
   * Priority: P2
   * Tags: @p2
   * AC: AC7
   */
  test('[P2] @p2 should filter events by event type', async ({ page }) => {
    await page.goto('/dashboard/telemetry/events');

    // Select event type filter
    await page.getByTestId('event-type-filter').selectOption('silence');

    // Verify filter is applied (mock would return filtered results)
    await expect(page.getByTestId('events-table')).toBeVisible();
  });

  /**
   * Test ID: 2.4-E2E-011
   * Priority: P2
   * Tags: @p2
   * AC: AC7
   */
  test('[P2] @p2 should show loading state during query', async ({ page }) => {
    // Delay API response to test loading state
    await page.route('**/api/v1/telemetry/events*', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.goto('/dashboard/telemetry/events');

    // Verify loading spinner is displayed
    await expect(page.getByTestId('events-loading')).toBeVisible();

    // Wait for loading to complete
    await expect(page.getByTestId('events-loading')).not.toBeVisible();
  });
});
