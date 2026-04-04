# Story 2.6: State Management Strategy

**Date**: 2026-04-04
**Author**: System Architect (Winston)
**Purpose**: Define interim state storage for Pre-Flight Calibration
**Status**: Approved for Implementation

---

## Problem Statement

**Adversarial Review Finding (Winston)**:
> "State Management Nightmare: AC5 requires no persistence on navigate-away, but AC6 requires pre-populating existing config. Where's the interim state stored? Local storage? Memory? This creates a fragile UX - if the user refreshes, they lose their adjustments."

**Acceptance Criteria Conflict**:
- **AC5**: "Given the user has not clicked 'Save Configuration', When they navigate away, Then no changes are persisted to the database"
- **AC6**: "Given the Pre-Flight module is loaded, When the module initializes, Then it fetches the current agent's voice configuration from the backend, And the sliders and controls are pre-populated with existing values"

**Gap**: What happens when user adjusts sliders → navigates away → returns? Without interim state storage, adjustments are lost.

---

## Approved Solution: localStorage with React Query

### Architecture Decision

```
┌─────────────────────────────────────────────────────────────┐
│                    Pre-Flight Calibration UI                 │
│                    (PreFlightCalibration.tsx)                │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ React Query mutations
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   React Query Cache                          │
│                   (Optimistic Updates)                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Sync
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   localStorage                               │
│                   (Key: agent-config-{agentId})              │
│                   (TTL: 1 hour)                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ On "Save Configuration"
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Backend API                                │
│                   (PUT /api/v1/agent-config)                 │
└─────────────────────────────────────────────────────────────┐
                              │
                              │ Persist
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   PostgreSQL                                 │
│                   (agent_configs table)                      │
└─────────────────────────────────────────────────────────────┘
```

### Why This Approach?

**localStorage Benefits**:
1. ✅ **Persists across page refreshes** (unlike in-memory state)
2. ✅ **Fast read/write** (<1ms vs. ~100ms for API call)
3. ✅ **Works offline** (can adjust sliders, sync when back online)
4. ✅ **Simple to implement** (native browser API)
5. ✅ **Automatic cleanup** with TTL (1 hour = reasonable session length)

**React Query Benefits**:
1. ✅ **Optimistic updates** (UI updates immediately, syncs in background)
2. ✅ **Automatic retries** on network failures
3. ✅ **Cache invalidation** when server data changes
4. ✅ **Loading/error states** built-in
5. ✅ **DevTools integration** for debugging

---

## Implementation Specification

### Data Model

**localStorage Schema**:

```typescript
// Key: agent-config-{agentId}
// Value: JSON string
// TTL: 1 hour (expires_at timestamp)

interface LocalStorageAgentConfig {
  agent_id: number;
  org_id: number;
  voice_id: string;
  voice_provider: 'elevenlabs' | 'cartesia' | 'openai';
  speech_speed: number;      // 0.5 - 2.0
  stability: number;         // 0.0 - 1.0
  temperature?: number;      // 0.0 - 1.0
  updated_at: string;        // ISO timestamp
  expires_at: string;        // ISO timestamp (now + 1 hour)
  has_unsaved_changes: boolean;  // True if localStorage ≠ DB
}
```

**Example localStorage Entry**:

```json
{
  "agent-config-123456": {
    "agent_id": 123456,
    "org_id": 12345,
    "voice_id": "eleven_turbo_v2",
    "voice_provider": "elevenlabs",
    "speech_speed": 1.2,
    "stability": 0.75,
    "temperature": 0.7,
    "updated_at": "2026-04-04T15:30:00Z",
    "expires_at": "2026-04-04T16:30:00Z",
    "has_unsaved_changes": true
  }
}
```

---

## Component Implementation

### PreFlightCalibration.tsx

```typescript
import { useQuery, useMutation } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

const LOCAL_STORAGE_KEY = (agentId: number) => `agent-config-${agentId}`;
const LOCAL_STORAGE_TTL_MS = 60 * 60 * 1000; // 1 hour

export function PreFlightCalibration({ agentId }: { agentId: number }) {
  const [localConfig, setLocalConfig] = useState<AgentConfig | null>(null);

  // Fetch persisted config from DB on mount
  const { data: dbConfig, isLoading } = useQuery({
    queryKey: ['agent-config', agentId],
    queryFn: () => getAgentConfig(agentId),
  });

  // Initialize from localStorage first (instant load), then DB
  useEffect(() => {
    const storageKey = LOCAL_STORAGE_KEY(agentId);
    const stored = localStorage.getItem(storageKey);

    if (stored) {
      const parsed = JSON.parse(stored);

      // Check TTL
      if (new Date(parsed.expires_at) > new Date()) {
        // Valid cache, use it
        setLocalConfig(parsed);
      } else {
        // Expired, remove it
        localStorage.removeItem(storageKey);
      }
    }

    // Once DB config loads, use that if no localStorage
    if (dbConfig && !localConfig) {
      setLocalConfig(dbConfig);
      // Write to localStorage for instant reload next time
      writeToLocalStorage(agentId, dbConfig);
    }
  }, [agentId, dbConfig]);

  // Handle slider changes
  const handleSliderChange = (field: 'speech_speed' | 'stability', value: number) => {
    const updated = {
      ...localConfig!,
      [field]: value,
      updated_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + LOCAL_STORAGE_TTL_MS).toISOString(),
      has_unsaved_changes: true,
    };

    setLocalConfig(updated);
    writeToLocalStorage(agentId, updated);
  };

  // Save to DB
  const saveMutation = useMutation({
    mutationFn: (config: AgentConfig) => updateAgentConfig(agentId, config),
    onSuccess: (savedConfig) => {
      // Clear unsaved flag
      const cleaned = {
        ...savedConfig,
        has_unsaved_changes: false,
      };
      setLocalConfig(cleaned);
      writeToLocalStorage(agentId, cleaned);
    },
  });

  return (
    <div>
      {/* Sliders update local state immediately */}
      <Slider
        value={localConfig?.speech_speed ?? 1.0}
        onChange={(value) => handleSliderChange('speech_speed', value)}
      />
      <Slider
        value={localConfig?.stability ?? 0.8}
        onChange={(value) => handleSliderChange('stability', value)}
      />

      {/* Save button persists to DB */}
      <button
        onClick={() => saveMutation.mutate(localConfig!)}
        disabled={!localConfig?.has_unsaved_changes || saveMutation.isPending}
      >
        Save Configuration
      </button>

      {localConfig?.has_unsaved_changes && (
        <p className="warning">You have unsaved changes</p>
      )}
    </div>
  );
}

// Helper: Write to localStorage with TTL
function writeToLocalStorage(agentId: number, config: AgentConfig) {
  const storageKey = LOCAL_STORAGE_KEY(agentId);
  const withExpiry = {
    ...config,
    expires_at: new Date(Date.now() + LOCAL_STORAGE_TTL_MS).toISOString(),
  };
  localStorage.setItem(storageKey, JSON.stringify(withExpiry));
}

// Helper: Read from localStorage (checks TTL)
function readFromLocalStorage(agentId: number): AgentConfig | null {
  const storageKey = LOCAL_STORAGE_KEY(agentId);
  const stored = localStorage.getItem(storageKey);

  if (!stored) return null;

  const parsed = JSON.parse(stored);

  // Check TTL
  if (new Date(parsed.expires_at) <= new Date()) {
    localStorage.removeItem(storageKey);
    return null;
  }

  return parsed;
}
```

---

## State Lifecycle

### Scenario 1: Normal Flow (Save)

```
1. User navigates to Pre-Flight module
   → Fetch DB config (1.0 speed, 0.8 stability)
   → Write to localStorage

2. User adjusts speech_speed slider to 1.5
   → Update localStorage (has_unsaved_changes: true)
   → Show "You have unsaved changes" warning

3. User clicks "Save Configuration"
   → PUT to /api/v1/agent-config
   → DB returns saved config
   → Update localStorage (has_unsaved_changes: false)
   → Hide warning

4. User navigates away
   → localStorage persists (1 hour TTL)

5. User returns within 1 hour
   → Load from localStorage (instant, no API call)
   → Show saved config (1.5 speed, has_unsaved_changes: false)
```

### Scenario 2: Abandon Changes (No Save)

```
1. User navigates to Pre-Flight module
   → Fetch DB config (1.0 speed, 0.8 stability)
   → Write to localStorage

2. User adjusts speech_speed slider to 1.8
   → Update localStorage (has_unsaved_changes: true)

3. User navigates away WITHOUT clicking Save
   → localStorage persists (has_unsaved_changes: true)

4. User returns within 1 hour
   → Load from localStorage
   → Show config (1.8 speed, has_unsaved_changes: true)
   → Show "You have unsaved changes from previous session"

5. User clicks "Discard Changes"
   → Clear localStorage
   → Fetch from DB (1.0 speed, 0.8 stability)
   → Write fresh to localStorage
```

### Scenario 3: TTL Expiration

```
1. User adjusts config (1.5 speed)
   → Write to localStorage (expires_at: now + 1 hour)

2. User navigates away

3. User returns AFTER 1 hour
   → Read localStorage
   → Check expires_at → EXPIRED
   → Remove from localStorage
   → Fetch from DB (1.0 speed)
   → Write fresh to localStorage
```

### Scenario 4: Page Refresh

```
1. User adjusts config (1.5 speed)
   → localStorage updated

2. User refreshes page (F5)
   → Component re-mounts
   → Read from localStorage (instant)
   → Show config (1.5 speed, has_unsaved_changes: true)
   → No API call needed
```

---

## Error Handling

### localStorage Failure

```typescript
function safeWriteToLocalStorage(agentId: number, config: AgentConfig) {
  try {
    writeToLocalStorage(agentId, config);
  } catch (error) {
    // localStorage might be full or disabled
    console.warn('localStorage write failed:', error);
    // Graceful degradation: continue without localStorage
    // User loses unsaved changes on refresh, but app still works
  }
}
```

### React Query Error Handling

```typescript
const { data: dbConfig, error, isLoading } = useQuery({
  queryKey: ['agent-config', agentId],
  queryFn: () => getAgentConfig(agentId),
  retry: 3, // Retry 3 times on failure
  onError: (error) => {
    // Show user-friendly error
    toast.error('Failed to load config. Please refresh.');
  },
});
```

---

## Testing Strategy

### Unit Tests

```typescript
describe('localStorage state management', () => {
  it('writes config to localStorage with TTL', () => {
    const config = createAgentConfig({ speech_speed: 1.5 });
    writeToLocalStorage(123456, config);

    const stored = localStorage.getItem('agent-config-123456');
    const parsed = JSON.parse(stored!);

    expect(parsed.speech_speed).toBe(1.5);
    expect(parsed.expires_at).toBeDefined();
  });

  it('returns null for expired entries', () => {
    const expiredConfig = {
      ...createAgentConfig(),
      expires_at: new Date(Date.now() - 1000).toISOString(), // 1 second ago
    };
    localStorage.setItem('agent-config-123456', JSON.stringify(expiredConfig));

    const result = readFromLocalStorage(123456);
    expect(result).toBeNull();
    expect(localStorage.getItem('agent-config-123456')).toBeNull(); // Cleaned up
  });
});
```

### Integration Tests

```typescript
describe('PreFlightCalibration state lifecycle', () => {
  it('persists unsaved changes across page refresh', async () => {
    const { getByLabelText } = render(<PreFlightCalibration agentId={123456} />);

    // Wait for DB config to load
    await waitFor(() => getByLabelText('Speech Speed'));

    // Adjust slider
    const slider = getByLabelText('Speech Speed');
    fireEvent.change(slider, { target: { value: 1.5 } });

    // Verify localStorage updated
    const stored = JSON.parse(localStorage.getItem('agent-config-123456')!);
    expect(stored.speech_speed).toBe(1.5);
    expect(stored.has_unsaved_changes).toBe(true);

    // Simulate page refresh
    window.location.reload();
    await waitFor(() => getByLabelText('Speech Speed'));

    // Verify config restored from localStorage
    const refreshedSlider = getByLabelText('Speech Speed');
    expect(refreshedSlider).toHaveValue(1.5);
  });
});
```

---

## Performance Considerations

### localStorage Read/Write Speed

- **Read**: <1ms (synchronous, no network)
- **Write**: <1ms (synchronous, no network)
- **JSON.parse/stringify**: <1ms for small objects

**Comparison to API**:
- API call: ~100-500ms (network latency + server processing)
- localStorage: ~1-2ms (instant)

### Cache Size Limits

- **localStorage limit**: 5-10MB per domain
- **Our usage**: ~500 bytes per config
- **Max configs**: 10,000+ before hitting limit

**Cleanup Strategy**:
- TTL automatically expires entries after 1 hour
- On component mount, clean expired entries
- Prevents localStorage bloat

---

## Security Considerations

### Tenant Isolation

**Risk**: localStorage is per-domain, not per-user.

**Mitigation**:
```typescript
// Always include org_id in localStorage key
const storageKey = `agent-config-${orgId}-${agentId}`;

// Verify org_id matches current user on read
function readFromLocalStorage(agentId: number, orgId: number): AgentConfig | null {
  const storageKey = `agent-config-${orgId}-${agentId}`;
  const stored = localStorage.getItem(storageKey);

  if (stored) {
    const parsed = JSON.parse(stored);
    // Verify org_id matches
    if (parsed.org_id !== orgId) {
      // Security: org mismatch, discard
      localStorage.removeItem(storageKey);
      return null;
    }
    return parsed;
  }

  return null;
}
```

### Data Sanitization

**Risk**: localStorage can be tampered with by user.

**Mitigation**:
- Always validate data on server (API endpoint validation)
- Never trust localStorage data as source of truth
- Use TypeScript types + runtime validation (zod)

```typescript
import { z } from 'zod';

const AgentConfigSchema = z.object({
  agent_id: z.number(),
  org_id: z.number(),
  voice_id: z.string(),
  speech_speed: z.number().min(0.5).max(2.0),
  stability: z.number().min(0.0).max(1.0),
  // ... other fields
});

function readFromLocalStorage(agentId: number): AgentConfig | null {
  const stored = localStorage.getItem(storageKey);
  if (!stored) return null;

  try {
    const parsed = JSON.parse(stored);
    // Validate with zod
    return AgentConfigSchema.parse(parsed);
  } catch {
    // Invalid data, discard
    localStorage.removeItem(storageKey);
    return null;
  }
}
```

---

## Accessibility

### Screen Reader Announcements

```typescript
function PreFlightCalibration({ agentId }: { agentId: number }) {
  const [announcer, setAnnouncer] = useState<string>('');

  const handleSliderChange = (field: string, value: number) => {
    // Update state...
    setAnnouncer(`${field} changed to ${value}`);
  };

  return (
    <>
      <div aria-live="polite" aria-atomic="true">
        {announcer}
      </div>
      <Slider
        aria-label="Speech Speed"
        value={localConfig?.speech_speed ?? 1.0}
        onChange={(value) => handleSliderChange('Speech Speed', value)}
      />
    </>
  );
}
```

---

## Updated Acceptance Criteria

**AC5 (REVISED)**:
```
Given the user has adjusted sliders but not clicked "Save Configuration",
When they navigate away from the Pre-Flight module,
Then their adjustments are persisted to localStorage (1-hour TTL),
And the previous agent configuration in the database remains unchanged,
And upon return, the UI shows "You have unsaved changes from previous session".
```

**AC6 (REVISED)**:
```
Given the Pre-Flight module is loaded,
When the module initializes,
Then it first reads from localStorage for instant load (<10ms),
Then it fetches the current agent's voice configuration from the backend,
And the sliders and controls are pre-populated with the freshest data,
And the UI displays a loading state during the fetch (if >100ms),
And unsaved changes from localStorage take priority over DB config.
```

---

## Dependencies

**Required Packages**:
```json
{
  "@tanstack/react-query": "^5.0.0",
  "zod": "^3.0.0"
}
```

**Installation**:
```bash
npm install @tanstack/react-query zod
```

---

## Related Decisions

- ADR: TTS Orchestrator Integration (provider abstraction)
- ADR: Caching Strategy for Audio Tests (Redis cache)
- Architecture: Client-Side State Management Pattern

---

## References

- React Query Documentation: https://tanstack.com/query/latest
- localStorage MDN: https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage
- Story 2.6: `_bmad-output/implementation-artifacts/2-6-pre-flight-calibration-dashboard.md`
- Adversarial Review Action Plan: Task 0b.2

---

**Last Updated**: 2026-04-04
**Status**: Approved for Implementation
**Owner**: System Architect (Winston) + Frontend Developer
**Next Action**: Implement in Phase 4 of Story 2.6
