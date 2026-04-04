"use server";

import { auth } from "@clerk/nextjs/server";
import type { VoicePreset as VoicePresetType, AgentConfigResponse } from "@call/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export interface VoicePreset {
  id: number;
  name: string;
  use_case: string;
  voice_id: string;
  speech_speed: number;
  stability: number;
  temperature: number;
  description: string;
  is_active: boolean;
  sort_order: number;
}

export interface VoicePresetRecommendation {
  preset_id: number;
  preset_name: string;
  improvement_pct: number;
  reasoning: string;
  based_on_calls: number;
}

export async function getVoicePresets(useCase?: string): Promise<{
  data: VoicePreset[] | null;
  error: string | null;
}> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { data: null, error: "Not authenticated" };

    const url = new URL(`${API_URL}/api/v1/voice-presets`);
    if (useCase) {
      url.searchParams.set("use_case", useCase);
    }

    const response = await fetch(url.toString(), {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!response.ok) {
      const err = await response.json();
      return { data: null, error: err.detail?.message || "Failed to fetch presets" };
    }

    const data = await response.json();
    return { data: data.presets, error: null };
  } catch (err) {
    return { data: null, error: err instanceof Error ? err.message : "Network error" };
  }
}

export async function getVoicePresetRecommendation(useCase: string): Promise<{
  data: VoicePresetRecommendation | null;
  reason: string | null;
  error: string | null;
}> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { data: null, reason: null, error: "Not authenticated" };

    const response = await fetch(
      `${API_URL}/api/v1/voice-presets/recommendations/${useCase}`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    if (!response.ok) {
      const err = await response.json();
      return { data: null, reason: null, error: err.detail?.message || "Failed to get recommendation" };
    }

    const result = await response.json();
    return { data: result.recommendation, reason: result.reason, error: null };
  } catch (err) {
    return { data: null, reason: null, error: err instanceof Error ? err.message : "Network error" };
  }
}

export async function selectVoicePreset(presetId: number): Promise<{
  data: { preset_id: number; message: string } | null;
  error: string | null;
}> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { data: null, error: "Not authenticated" };

    const response = await fetch(
      `${API_URL}/api/v1/voice-presets/${presetId}/select`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      }
    );

    if (!response.ok) {
      const err = await response.json();
      return { data: null, error: err.detail?.message || "Selection failed" };
    }

    const data = await response.json();
    return { data, error: null };
  } catch (err) {
    return { data: null, error: err instanceof Error ? err.message : "Network error" };
  }
}

export async function getPresetSample(presetId: number): Promise<{
  data: Blob | null;
  error: string | null;
}> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { data: null, error: "Not authenticated" };

    const response = await fetch(
      `${API_URL}/api/v1/voice-presets/${presetId}/sample`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    if (!response.ok) {
      const err = await response.json();
      return {
        data: null,
        error: err.detail?.message || "Failed to get sample",
      };
    }

    const blob = await response.blob();
    return { data: blob, error: null };
  } catch (err) {
    return { data: null, error: err instanceof Error ? err.message : "Network error" };
  }
}

export async function getCurrentAgentConfig(): Promise<{
  data: AgentConfigResponse | null;
  error: string | null;
}> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { data: null, error: "Not authenticated" };

    const response = await fetch(`${API_URL}/api/v1/agent-config/current`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!response.ok) {
      const err = await response.json();
      return {
        data: null,
        error: err.detail?.message || "Failed to get agent config",
      };
    }

    const data = await response.json();
    return { data, error: null };
  } catch (err) {
    return { data: null, error: err instanceof Error ? err.message : "Network error" };
  }
}

export async function saveAdvancedVoiceConfig(config: {
  speech_speed: number;
  stability: number;
  temperature: number;
}): Promise<{
  data: { message: string } | null;
  error: string | null;
}> {
  try {
    const { getToken } = await auth();
    const token = await getToken();
    if (!token) return { data: null, error: "Not authenticated" };

    const response = await fetch(`${API_URL}/api/v1/agent-config/advanced`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        speech_speed: config.speech_speed,
        stability: config.stability,
        temperature: config.temperature,
        use_advanced_mode: true,
        preset_id: null,
      }),
    });

    if (!response.ok) {
      const err = await response.json();
      return { data: null, error: err.detail?.message || "Failed to save config" };
    }

    const data = await response.json();
    return { data, error: null };
  } catch (err) {
    return { data: null, error: err instanceof Error ? err.message : "Network error" };
  }
}

export interface AgentConfigResponse {
  preset_id: number | null;
  speech_speed: number;
  stability: number;
  temperature: number;
  use_advanced_mode: boolean;
}

export interface AdvancedConfig {
  speech_speed: number;
  stability: number;
  temperature: number;
}
