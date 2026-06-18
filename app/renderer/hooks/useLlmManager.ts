import { useState, useCallback } from "react";

export interface LlmProvider {
    id: string;
    type: string;
    base_url: string;
    api_key?: string;
    models: string[]; // Normalized to array in front-end
    enabled: boolean;
}

export interface LlmRoute {
    feature: string;
    provider_id: string;
    model: string;
    temperature?: number;
    top_p?: number;
    presence_penalty?: number;
    frequency_penalty?: number;
}

export const useLlmManager = (apiBaseUrl: string) => {
    const [llmRoutes, setLlmRoutes] = useState<LlmRoute[]>([]);
    const [llmProviders, setLlmProviders] = useState<LlmProvider[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const refreshData = useCallback(async () => {
        setIsLoading(true);
        setError(null);
        try {
            const [routesRes, provRes] = await Promise.all([
                fetch(`${apiBaseUrl}/settings/llm/routes`),
                fetch(`${apiBaseUrl}/settings/llm/providers`),
            ]);

            if (!routesRes.ok || !provRes.ok) {
                throw new Error(
                    `API Error: Routes=${routesRes.status}, Prov=${provRes.status}`,
                );
            }

            const rData = await routesRes.json();
            const pData = await provRes.json();
            setLlmRoutes(rData.routes || []);
            setLlmProviders(pData.providers || []);
        } catch (e: any) {
            console.error("[useLlmManager] Failed to fetch data", e);
            setError(e.message || "Failed to load LLM data");
        } finally {
            setIsLoading(false);
        }
    }, [apiBaseUrl]);

    const addProvider = async (config: {
        id: string;
        type: string;
        base_url: string;
        api_key: string;
        models: string[];
    }) => {
        setError(null);
        try {
            const payload = {
                ...config,
                enabled: true,
            };
            const res = await fetch(
                `${apiBaseUrl}/settings/llm/providers/${config.id}`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                },
            );
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Failed to add provider");
            }
            await refreshData();
            return true;
        } catch (e: any) {
            console.error("[useLlmManager] Failed to add provider", e);
            setError(e.message);
            return false;
        }
    };

    const updateProvider = async (id: string, updates: any) => {
        try {
            await fetch(`${apiBaseUrl}/settings/llm/providers/${id}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(updates),
            });
            await refreshData();
            return true;
        } catch (e) {
            console.error("[useLlmManager] Failed to update provider", e);
            return false;
        }
    };

    const updateRoute = async (
        feature: string,
        payload: {
            provider_id?: string;
            model?: string;
            temperature?: number;
            top_p?: number;
            presence_penalty?: number;
            frequency_penalty?: number;
        },
    ) => {
        try {
            const res = await fetch(
                `${apiBaseUrl}/settings/llm/routes/${feature}`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                },
            );
            if (res.ok) {
                await refreshData();
                return true;
            }
            return false;
        } catch (e) {
            console.error("[useLlmManager] Failed to update route", e);
            return false;
        }
    };

    return {
        llmRoutes,
        setLlmRoutes,
        llmProviders,
        isLoading,
        refreshData,
        addProvider,
        updateProvider,
        updateRoute,
        error,
    };
};
