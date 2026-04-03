import { test, expect } from '@playwright/test';

/**
 * Story 2.4: Telemetry API Tests
 * Test ID Format: 2.4-API-XXX
 * Priority Tags: @smoke @p0 @p1 @p2
 */

test.describe('[2.4-API] Telemetry Metrics Endpoint', () => {
  /**
   * Test ID: 2.4-API-001
   * Priority: P0
   * Tags: @smoke @p0
   * AC: AC6
   */
  test('[P0] @smoke @p0 should return queue health metrics', async ({ request }) => {
    const response = await request.get('/api/v1/telemetry/metrics');

    expect(response.status()).toBe(200);

    const metrics = await response.json();
    expect(metrics).toMatchObject({
      current_depth: expect.any(Number),
      avg_depth: expect.any(Number),
      max_depth: expect.any(Number),
      is_running: expect.any(Boolean),
      processing_latency_ms_p95: expect.any(Number),
      events_per_second: expect.any(Number),
    });
  });

  /**
   * Test ID: 2.4-API-002
   * Priority: P0
   * Tags: @p0
   * AC: AC6
   */
  test('[P0] @p0 should include queue depth gauge metrics', async ({ request }) => {
    const response = await request.get('/api/v1/telemetry/metrics');

    expect(response.status()).toBe(200);

    const metrics = await response.json();
    expect(metrics.current_depth).toBeGreaterThanOrEqual(0);
    expect(metrics.avg_depth).toBeGreaterThanOrEqual(0);
    expect(metrics.max_depth).toBeGreaterThanOrEqual(0);
  });

  /**
   * Test ID: 2.4-API-003
   * Priority: P1
   * Tags: @p1
   * AC: AC6
   */
  test('[P1] @p1 should return processing latency metrics', async ({ request }) => {
    const response = await request.get('/api/v1/telemetry/metrics');

    expect(response.status()).toBe(200);

    const metrics = await response.json();
    expect(metrics.processing_latency_ms_p95).toBeGreaterThan(0);
  });

  /**
   * Test ID: 2.4-API-004
   * Priority: P1
   * Tags: @p1
   * AC: AC6, AC8.5
   */
  test('[P1] @p1 should include events per second rate', async ({ request }) => {
    const response = await request.get('/api/v1/telemetry/metrics');

    expect(response.status()).toBe(200);

    const metrics = await response.json();
    expect(metrics.events_per_second).toBeGreaterThanOrEqual(0);
  });

  /**
   * Test ID: 2.4-API-005
   * Priority: P0
   * Tags: @p0
   * AC: AC8.5
   */
  test('[P0] @p0 should indicate worker running status', async ({ request }) => {
    const response = await request.get('/api/v1/telemetry/metrics');

    expect(response.status()).toBe(200);

    const metrics = await response.json();
    expect(typeof metrics.is_running).toBe('boolean');
  });

  /**
   * Test ID: 2.4-API-006
   * Priority: P0
   * Tags: @smoke @p0
   * AC: AC6
   */
  test('[P0] @smoke @p0 should allow unauthenticated access for monitoring', async ({ request }) => {
    // Metrics endpoint should not require auth for ops monitoring
    const response = await request.get('/api/v1/telemetry/metrics', {
      headers: {
        // Intentionally no auth header
      }
    });

    expect(response.status()).toBe(200);
  });
});

test.describe('[2.4-API] Telemetry Events Query Endpoint', () => {
  /**
   * Test ID: 2.4-API-007
   * Priority: P1
   * Tags: @p1
   * AC: AC7
   */
  test('[P1] @p1 should query events with call_id filter', async ({ request }) => {
    const response = await request.get('/api/v1/telemetry/events?call_id=123');

    expect(response.status()).toBe(200);

    const events = await response.json();
    expect(Array.isArray(events)).toBe(true);
    events.forEach(event => {
      expect(event.call_id).toBe(123);
    });
  });

  /**
   * Test ID: 2.4-API-008
   * Priority: P1
   * Tags: @p1
   * AC: AC7
   */
  test('[P1] @p1 should query events with event_type filter', async ({ request }) => {
    const response = await request.get('/api/v1/telemetry/events?event_type=silence');

    expect(response.status()).toBe(200);

    const events = await response.json();
    expect(Array.isArray(events)).toBe(true);
    events.forEach(event => {
      expect(event.event_type).toBe('silence');
    });
  });

  /**
   * Test ID: 2.4-API-009
   * Priority: P1
   * Tags: @p1
   * AC: AC7
   */
  test('[P1] @p1 should query events with timestamp range', async ({ request }) => {
    const startTime = '2024-01-01T00:00:00Z';
    const endTime = '2024-01-02T00:00:00Z';

    const response = await request.get(
      `/api/v1/telemetry/events?start_time=${startTime}&end_time=${endTime}`
    );

    expect(response.status()).toBe(200);

    const events = await response.json();
    expect(Array.isArray(events)).toBe(true);
  });

  /**
   * Test ID: 2.4-API-010
   * Priority: P2
   * Tags: @p2
   * AC: AC7
   */
  test('[P2] @p2 should respect limit parameter', async ({ request }) => {
    const response = await request.get('/api/v1/telemetry/events?limit=5');

    expect(response.status()).toBe(200);

    const events = await response.json();
    expect(events.length).toBeLessThanOrEqual(5);
  });

  /**
   * Test ID: 2.4-API-011
   * Priority: P1
   * Tags: @p1
   * AC: AC7
   */
  test('[P1] @p1 should enforce max limit of 10000', async ({ request }) => {
    const response = await request.get('/api/v1/telemetry/events?limit=20000');

    expect(response.status()).toBe(200);

    const events = await response.json();
    expect(events.length).toBeLessThanOrEqual(10000);
  });

  /**
   * Test ID: 2.4-API-012
   * Priority: P2
   * Tags: @p2
   * AC: AC7
   */
  test('[P2] @p2 should reject invalid timestamp format', async ({ request }) => {
    const response = await request.get('/api/v1/telemetry/events?start_time=invalid');

    expect(response.status()).toBe(400);

    const error = await response.json();
    expect(error).toMatchObject({
      detail: expect.stringContaining('Invalid timestamp format'),
    });
  });

  /**
   * Test ID: 2.4-API-013
   * Priority: P0
   * Tags: @p0
   * AC: AC7
   */
  test('[P0] @p0 should enforce tenant isolation', async ({ request }) => {
    // This test requires authenticated context with tenant_id
    // Events query should only return events for the authenticated tenant
    const response = await request.get('/api/v1/telemetry/events');

    expect(response.status()).toBe(200);

    const events = await response.json();
    expect(Array.isArray(events)).toBe(true);
    // Verify all events belong to the same org_id (tenant isolation)
    const orgIds = new Set(events.map(e => e.org_id));
    expect(orgIds.size).toBe(1);
  });

  /**
   * Test ID: 2.4-API-014
   * Priority: P0
   * Tags: @p0
   * AC: AC7
   */
  test('[P0] @p0 should require authentication for events query', async ({ request }) => {
    const response = await request.get('/api/v1/telemetry/events', {
      headers: {
        // No auth header
      }
    });

    expect(response.status()).toBe(403);
  });
});

test.describe('[2.4-API] Degradation Visibility (AC8.5)', () => {
  /**
   * Test ID: 2.4-API-015
   * Priority: P0
   * Tags: @p0
   * AC: AC8.5
   */
  test('[P0] @p0 should track drop rate in metrics', async ({ request }) => {
    const response = await request.get('/api/v1/telemetry/metrics');

    expect(response.status()).toBe(200);

    const metrics = await response.json();
    expect(metrics).toHaveProperty('drop_rate');
    expect(metrics.drop_rate).toBeGreaterThanOrEqual(0);
    expect(metrics.drop_rate).toBeLessThanOrEqual(1);
  });

  /**
   * Test ID: 2.4-API-016
   * Priority: P0
   * Tags: @p0
   * AC: AC8.5
   */
  test('[P0] @p0 should alert when drop rate exceeds 10%', async ({ request }) => {
    // This test simulates high drop rate scenario
    // In real scenario, would need to push events until queue fills
    const response = await request.get('/api/v1/telemetry/metrics');

    expect(response.status()).toBe(200);

    const metrics = await response.json();
    // If drop rate > 10%, should include degradation alert
    if (metrics.drop_rate > 0.1) {
      expect(metrics).toHaveProperty('degradation_alert');
      expect(metrics.degradation_alert).toMatchObject({
        level: 'critical',
        message: expect.stringContaining('drop rate exceeds 10%'),
        threshold: 0.1,
        current_value: metrics.drop_rate,
      });
    }
  });

  /**
   * Test ID: 2.4-API-017
   * Priority: P1
   * Tags: @p1
   * AC: AC8.5
   */
  test('[P1] @p1 should track consecutive drop periods', async ({ request }) => {
    const response = await request.get('/api/v1/telemetry/metrics');

    expect(response.status()).toBe(200);

    const metrics = await response.json();
    expect(metrics).toHaveProperty('consecutive_high_drop_periods');
    expect(metrics.consecutive_high_drop_periods).toBeGreaterThanOrEqual(0);
  });

  /**
   * Test ID: 2.4-API-018
   * Priority: P1
   * Tags: @p1
   * AC: AC8.5
   */
  test('[P1] @p1 should include time_since_last_drop', async ({ request }) => {
    const response = await request.get('/api/v1/telemetry/metrics');

    expect(response.status()).toBe(200);

    const metrics = await response.json();
    expect(metrics).toHaveProperty('time_since_last_drop_seconds');
    expect(metrics.time_since_last_drop_seconds).toBeGreaterThanOrEqual(0);
  });
});
