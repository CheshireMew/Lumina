import { useState, useCallback } from "react";
import { API_CONFIG } from "../config";

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

export const useLlmManager = () => {
    const [llmRoutes, setLlmRoutes] = useState<LlmRoute[]>([]);
    const [llmProviders, setLlmProviders] = useState<LlmProvider[]>([]);
    const [isLoading, setIsLoading] = useState(false);

    const refreshData = useCallback(async () => {
        setIsLoading(true);
        try {
            const [routesRes, provRes] = await Promise.all([
                fetch(`${API_CONFIG.BASE_URL}/llm-mgmt/routes`),
                fetch(`${API_CONFIG.BASE_URL}/llm-mgmt/providers`),
            ]);

            if (routesRes.ok && provRes.ok) {
                const rData = await routesRes.json();
                const pData = await provRes.json();
                setLlmRoutes(rData.routes || []);
                setLlmProviders(pData.providers || []);
            }
        } catch (e) {
            console.error("[useLlmManager] Failed to fetch data", e);
        } finally {
            setIsLoading(false);
        }
    }, []);

    const addProvider = async (config: {
        id: string;
        type: string;
        base_url: string;
        api_key: string;
        models: string[];
    }) => {
        try {
            const payload = {
                ...config,
                enabled: true,
            };
            const res = await fetch(
                `${API_CONFIG.BASE_URL}/llm-mgmt/providers/${config.id}`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                }
            );
            if (res.ok) {
                await refreshData();
                return true;
            }
            return false;
        } catch (e) {
            console.error("[useLlmManager] Failed to add provider", e);
            return false;
        }
    };

    const updateProvider = async (id: string, updates: any) => {
        try {
            await fetch(`${API_CONFIG.BASE_URL}/llm-mgmt/providers/${id}`, {
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
        }
    ) => {
        try {
            const res = await fetch(
                `${API_CONFIG.BASE_URL}/llm-mgmt/routes/${feature}`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                }
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
    };
};
