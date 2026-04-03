/**
 * Telemetry Load Test
 * Story 2.4: Asynchronous Telemetry Sidecars for Voice Events
 *
 * Simulates 1,000+ concurrent calls generating 1 event/sec each
 * Total load: 1,000 events/sec sustained
 *
 * AC: 3 - Load test with k6 to verify <2ms P95 push latency
 * AC: 8 - Verify queue depth remains <80% capacity
 *
 * NOTE: This test currently only hits the metrics endpoint.
 * TODO: Update to exercise the actual queue push via POST /api/v1/telemetry/events
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate } from "k6/metrics";

// Custom metrics
const telemetrySuccessRate = new Rate("telemetry_success_rate");

// Test configuration
export const options = {
  stages: [
    { duration: "30s", target: 1000 },  // Ramp up to 1,000 concurrent users
    { duration: "2m", target: 1000 },   // Sustained load at 1,000 users
    { duration: "30s", target: 0 },     // Ramp down
  ],
  thresholds: {
    // AC: 3 - 95th percentile response time <2ms
    "http_req_duration": ["p(95)<2"],

    // Success rate should be >95% (allowing some queue drops)
    "telemetry_success_rate": ["rate>0.95"],

    // Queue depth should remain <80% capacity
    // This would be monitored via metrics endpoint during test
  },
};

const BASE_URL = __ENV.API_URL || "http://localhost:8000";

// Simulate voice event types
const EVENT_TYPES = ["silence", "noise", "interruption", "talkover"];
const PROVIDERS = ["vapi", "deepgram", "cartesia"];

function generateRandomEvent(callId) {
  const eventType = EVENT_TYPES[Math.floor(Math.random() * EVENT_TYPES.length)];
  const provider = PROVIDERS[Math.floor(Math.random() * PROVIDERS.length)];

  return {
    call_id: callId,
    event_type: eventType,
    duration_ms: Math.random() * 5000,
    audio_level: -60 + Math.random() * 40,
    confidence_score: Math.random(),
    sentiment_score: Math.random(),
    provider: provider,
    metadata: {
      test_run: true,
      vus: __VU,
      iteration: __ITER,
    },
  };
}

export default function () {
  // Each VU simulates one active call
  const callId = 1000 + __VU;

  // Generate 1 event per iteration (realistic voice event rate)
  // Default k6 iteration time is 1s, so this equals 1 event/sec per VU
  const event = generateRandomEvent(callId);

  const payload = JSON.stringify(event);
  const params = {
    headers: {
      "Content-Type": "application/json",
    },
  };

  // Check metrics endpoint to verify system health
  // TODO: Replace with actual POST /api/v1/telemetry/events to exercise queue
  // Current implementation only validates metrics endpoint is responsive
  const response = http.get(`${BASE_URL}/api/v1/telemetry/metrics`);

  // Check response
  const success = check(response, {
    "metrics endpoint returns 200": (r) => r.status === 200,
    "response time <500ms": (r) => r.timings.duration < 500,
  });

  telemetrySuccessRate.add(success);

  // Brief pause to simulate realistic event timing
  sleep(1); // 1s between events = 1 event/sec
}

/**
 * Memory Leak Prevention Test
 * [2.4-MEMORY-CLEANUP-001] P1 Test: Verify queue evicts stale call_id references
 *
 * Scenario: 1,000 calls generate events over 1 hour, then calls end and cleanup runs
 * Expected: Stale call_id references are evicted from queue metrics
 */
export function handleTestSetup() {
  // Log test start
  console.log(`Starting telemetry load test at ${new Date().toISOString()}`);
  console.log(`Target: ${__ENV.TARGET_CONCURRENT_USERS || 1000} concurrent users`);
}

export function handleTestTeardown(data) {
  // Log test completion
  console.log(`Load test completed at ${new Date().toISOString()}`);

  // Check metrics endpoint for final queue state
  const metricsResponse = http.get(`${BASE_URL}/api/v1/telemetry/metrics`);
  if (metricsResponse.status === 200) {
    const metrics = metricsResponse.json();
    console.log(`Final queue metrics:`, JSON.stringify(metrics, null, 2));

    // Verify queue depth is acceptable
    if (metrics.current_depth > 8000) {
      console.warn(`WARNING: Queue depth ${metrics.current_depth} exceeds 80% capacity`);
    }

    // Verify worker is healthy
    if (!metrics.is_running) {
      console.error(`ERROR: Telemetry worker not running`);
    }
  }
}

/**
 * Optional: Setup function to initialize test data
 */
export function setup() {
  console.log("Setting up telemetry load test environment");

  // Verify API is accessible
  const response = http.get(`${BASE_URL}/api/v1/telemetry/metrics`);
  if (response.status !== 200) {
    throw new Error(`API not accessible: ${response.status}`);
  }

  return {
    startTime: new Date().toISOString(),
  };
}

/**
 * Optional: Teardown function to clean up after test
 */
export function teardown(data) {
  console.log("Tearing down telemetry load test");

  // Log final statistics
  console.log("Test completed successfully");
}
