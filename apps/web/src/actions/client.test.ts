/**
 * Story 1-2: Multi-layer Hierarchy & Clerk Auth Integration
 * Unit Tests for Client Server Actions
 * 
 * Test ID Format: 1.2-UNIT-CLIENT-XXX
 * Priority: P0 (Critical) | P1 (High) | P2 (Medium) | P3 (Low)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createClient, updateClient, deleteClient, getClients } from './client';
import type { Client, ClientSettings } from '@call/types';

const mockFetch = vi.fn();
global.fetch = mockFetch;

const ORG_IDS = {
  validOrgId: 'org_2QWXJC123456',
}

const CLIENT_IDS = {
  validClientId: 'client_abc123456',
}

describe('[P0] Client Server Actions - AC2', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  })
  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('createClient', () => {
    it('[1.2-UNIT-CLIENT-001][P0] should create client under organization', async () => {
      const clientData = {
        orgId: ORG_IDS.validOrgId,
        name: 'Test Client',
        settings: { timezone: 'UTC' },
      };
      const mockResponse = { 
        id: CLIENT_IDS.validClientId,
        ...clientData,
        orgId: ORG_IDS.validOrgId,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await createClient(clientData);

      expect(result.client).toEqual(mockResponse)
      expect(result.error).toBeNull()
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/organizations/${ORG_IDS.validOrgId}/clients`),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
        })
      );
    });

    it('[1.2-UNIT-CLIENT-002][P1] should return error when creation fails', async () => {
      const clientData = {
        orgId: ORG_IDS.validOrgId,
        name: 'Test Client',
        settings: { timezone: 'UTC' },
      }
      
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ message: 'Failed to create client' }),
      })

      const result = await createClient(clientData)

      expect(result.client).toBeNull()
      expect(result.error).toBe('Failed to create client')
    });

    it('[1.2-UNIT-CLIENT-003][P2] should handle network errors', async () => {
      const clientData = {
        orgId: ORG_IDS.validOrgId,
        name: 'Test Client',
      }
      
      mockFetch.mockRejectedValueOnce(new Error('Network error'))

      const result = await createClient(clientData)

      expect(result.client).toBeNull()
      expect(result.error).toBe('Network error')
    });
  });

  describe('updateClient', () => {
    it('[1.2-UNIT-CLIENT-004][P1] should update client', async () => {
      const updates = { name: 'Updated Client' };
      const mockResponse = { 
        id: CLIENT_IDS.validClientId,
        orgId: ORG_IDS.validOrgId,
        ...updates,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const result = await updateClient({
        orgId: ORG_IDS.validOrgId,
        clientId: CLIENT_IDS.validClientId,
        updates: updates,
      });

      expect(result.client).toEqual(mockResponse)
      expect(result.error).toBeNull();
    });

    it('[1.2-UNIT-CLIENT-005][P1] should return error when update fails', async () => {
      const updates = { name: 'Updated Client' };
      
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ message: 'Client not found' }),
      })

      const result = await updateClient({
        orgId: ORG_IDS.validOrgId,
        clientId: CLIENT_IDS.validClientId,
        updates: updates,
      });

      expect(result.client).toBeNull()
      expect(result.error).toBe('Client not found')
    });
  });

  describe('deleteClient', () => {
    it('[1.2-UNIT-CLIENT-006][P1] should delete client', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true }),
      });

      const result = await deleteClient({
        orgId: ORG_IDS.validOrgId,
        clientId: CLIENT_IDS.validClientId,
      });

      expect(result.success).toBe(true)
      expect(result.error).toBeNull();
    });

    it('[1.2-UNIT-CLIENT-007][P1] should return error when delete fails', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ message: 'Unauthorized' }),
      });

      const result = await deleteClient({
        orgId: ORG_IDS.validOrgId,
        clientId: CLIENT_IDS.validClientId,
      });

      expect(result.success).toBe(false)
      expect(result.error).toBe('Unauthorized')
    });
  });

  describe('getClients', () => {
    it('[1.2-UNIT-CLIENT-008][P1] should return clients for organization', async () => {
      const mockClients = [
        { id: CLIENT_IDS.validClientId, orgId: ORG_IDS.validOrgId, name: 'Client 1' },
        { id: 'client_xyz789', orgId: ORG_IDS.validOrgId, name: 'Client 2' },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockClients,
      })

      const result = await getClients(ORG_IDS.validOrgId);

      expect(result.clients).toEqual(mockClients)
      expect(result.error).toBeNull()
    });

    it('[1.2-UNIT-CLIENT-009][P1] should return empty array on error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ message: 'Organization not found' }),
      })

      const result = await getClients(ORG_IDS.validOrgId);

      expect(result.clients).toEqual([])
      expect(result.error).toBe('Organization not found')
    });

    it('[1.2-UNIT-CLIENT-010][P2] should handle fetch errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Connection failed'))

      const result = await getClients(ORG_IDS.validOrgId);

      expect(result.clients).toEqual([])
      expect(result.error).toBe('Connection failed')
    });
  });
});
