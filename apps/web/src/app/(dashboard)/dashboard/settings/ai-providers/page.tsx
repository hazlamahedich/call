"use client";

import { useState, useEffect, useCallback } from "react";
import { useOrganization } from "@clerk/nextjs";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusMessage } from "@/components/ui/status-message";
import {
  ProviderSelector,
  ModelSelector,
  ApiKeyInput,
  ConnectionStatus,
} from "@/components/ai-providers";
import {
  getAIProviderConfig,
  updateAIProviderConfig,
  testAIProviderConnection,
  getAvailableModels,
} from "@/actions/ai-providers";
import type { AIProvider, AIProviderConfig } from "@call/types";

export default function AIProvidersSettingsPage() {
  const { organization } = useOrganization();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [message, setMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  const [provider, setProvider] = useState<AIProvider>("openai");
  const [apiKey, setApiKey] = useState("");
  const [hasExistingKey, setHasExistingKey] = useState(false);
  const [embeddingModel, setEmbeddingModel] = useState(
    "text-embedding-3-small",
  );
  const [llmModel, setLlmModel] = useState("gpt-4o-mini");
  const [connectionStatus, setConnectionStatus] = useState<
    "connected" | "disconnected" | "untested"
  >("untested");
  const [availableModels, setAvailableModels] = useState<
    Record<string, { embedding: string[]; llm: string[] }>
  >({});

  useEffect(() => {
    if (!organization) return;
    setLoading(true);
    Promise.all([
      getAIProviderConfig(organization.id),
      getAvailableModels(organization.id),
    ]).then(([configResult, modelsResult]) => {
      if (configResult.data) {
        const cfg = configResult.data;
        setProvider(cfg.provider);
        setEmbeddingModel(cfg.embeddingModel);
        setLlmModel(cfg.llmModel);
        setHasExistingKey(cfg.hasApiKey);
        setConnectionStatus(cfg.connectionStatus);
      }
      if (modelsResult.data) {
        setAvailableModels(modelsResult.data);
      }
      setLoading(false);
    });
  }, [organization]);

  const handleTest = useCallback(async () => {
    if (!organization) return;
    setTesting(true);
    const { data, error } = await testAIProviderConnection(organization.id);
    if (error) {
      setConnectionStatus("disconnected");
      setMessage({ type: "error", text: error });
    } else if (data) {
      setConnectionStatus(data.success ? "connected" : "disconnected");
      setMessage({
        type: data.success ? "success" : "error",
        text: data.message,
      });
    }
    setTesting(false);
  }, [organization]);

  const handleSave = useCallback(async () => {
    if (!organization) return;
    if (!apiKey && !hasExistingKey) {
      setMessage({ type: "error", text: "API key is required" });
      return;
    }
    setSaving(true);
    setMessage(null);

    const { data, error } = await updateAIProviderConfig(organization.id, {
      provider,
      apiKey: apiKey || "KEEP_EXISTING",
      embeddingModel,
      llmModel,
    });
    if (error) {
      setMessage({ type: "error", text: error });
    } else if (data) {
      setHasExistingKey(data.hasApiKey);
      setConnectionStatus(data.connectionStatus);
      setApiKey("");
      setMessage({ type: "success", text: "AI provider settings saved" });
    }
    setSaving(false);
  }, [
    organization,
    provider,
    apiKey,
    hasExistingKey,
    embeddingModel,
    llmModel,
  ]);

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <div className="size-8 animate-spin rounded-full border-2 border-border border-t-neon-emerald" />
      </div>
    );
  }

  const models = availableModels[provider] || { embedding: [], llm: [] };

  return (
    <div className="mx-auto max-w-2xl space-y-lg p-lg">
      <div>
        <h1 className="text-lg font-semibold text-foreground">
          AI Provider Settings
        </h1>
        <p className="text-sm text-muted-foreground">
          Configure your AI provider for embeddings and language models
        </p>
      </div>

      {message && (
        <StatusMessage variant={message.type}>{message.text}</StatusMessage>
      )}

      <Card variant="standard" className="p-0">
        <CardHeader>
          <CardTitle>Provider</CardTitle>
          <CardDescription>
            Select your AI provider for embeddings and LLM
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ProviderSelector
            value={provider}
            onChange={(p) => {
              setProvider(p);
              const m = availableModels[p];
              if (m) {
                setEmbeddingModel(m.embedding[0]);
                setLlmModel(m.llm[0]);
              }
            }}
          />
        </CardContent>
      </Card>

      <Card variant="standard" className="p-0">
        <CardHeader>
          <CardTitle>API Key</CardTitle>
          <CardDescription>
            Enter your {provider === "openai" ? "OpenAI" : "Google Gemini"} API
            key
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <ApiKeyInput
            value={apiKey}
            hasExistingKey={hasExistingKey}
            onChange={setApiKey}
          />
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={handleTest}
              disabled={testing || (!apiKey && !hasExistingKey)}
            >
              {testing ? "Testing..." : "Test Connection"}
            </Button>
            <ConnectionStatus status={connectionStatus} testing={testing} />
          </div>
        </CardContent>
      </Card>

      <Card variant="standard" className="p-0">
        <CardHeader>
          <CardTitle>Models</CardTitle>
          <CardDescription>
            Select embedding and LLM models for the chosen provider
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <ModelSelector
              label="Embedding Model"
              value={embeddingModel}
              options={models.embedding}
              onChange={setEmbeddingModel}
            />
            <ModelSelector
              label="LLM Model"
              value={llmModel}
              options={models.llm}
              onChange={setLlmModel}
            />
          </div>
          {provider === "gemini" && (
            <p className="text-xs text-amber-500">
              Switching to Gemini requires re-ingesting all documents (different
              embedding dimensions)
            </p>
          )}
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button
          variant="primary"
          size="md"
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? "Saving..." : "Save Changes"}
        </Button>
      </div>
    </div>
  );
}
