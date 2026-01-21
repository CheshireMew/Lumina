import { useState, useEffect, useCallback } from "react";
import { API_CONFIG } from "../config";

export interface UiSlot {
    plugin_id: string;
    slot: string;
    name: string;
    src: string;
    width?: string | number;
    height?: number;
    _source?: string;
    _token?: string;
}

export const usePluginSlots = () => {
    const [slots, setSlots] = useState<UiSlot[]>([]);
    const [isLoading, setIsLoading] = useState(false);

    const fetchSlots = useCallback(async () => {
        setIsLoading(true);
        try {
            const res = await fetch(`${API_CONFIG.BASE_URL}/plugins/slots`);
            if (res.ok) {
                const data = await res.json();
                const rawSlots = data.slots || [];

                // [Validation] Filter invalid slots from API
                const validSlots = rawSlots.filter((s: any) => {
                    if (!s.plugin_id || !s.name || !s.slot || !s.src) {
                        console.warn(
                            "[usePluginSlots] Dropped invalid slot from API:",
                            s,
                        );
                        return false;
                    }
                    return true;
                });

                setSlots(validSlots);
            }
        } catch (e) {
            console.error("[usePluginSlots] Failed to fetch slots", e);
        } finally {
            setIsLoading(false);
        }
    }, []);

    // Initial Load & Event Listening
    useEffect(() => {
        fetchSlots();

        const handleWidgetEvent = (e: Event) => {
            const customEvent = e as CustomEvent;
            const { type, payload } = customEvent.detail;

            if (type === "ui:register_widget") {
                console.log("[usePluginSlots] New Widget:", payload);
                // [Validation] Ensure payload matches UiSlot schema
                if (
                    !payload ||
                    !payload.plugin_id ||
                    !payload.slot ||
                    !payload.name ||
                    !payload.src
                ) {
                    console.warn(
                        "[usePluginSlots] Invalid Widget Payload:",
                        payload,
                    );
                    return;
                }

                setSlots((prev) => {
                    // [Fix] Match Backend Deduplication Logic (Plugin + Slot + Name)
                    const index = prev.findIndex(
                        (s) =>
                            s.plugin_id === payload.plugin_id &&
                            s.slot === payload.slot &&
                            s.name === payload.name,
                    );

                    if (index !== -1) {
                        // Update existing (Fixes stale state vs new event)
                        const newSlots = [...prev];
                        newSlots[index] = { ...newSlots[index], ...payload };
                        return newSlots;
                    }
                    return [...prev, payload];
                });
            } else if (
                type === "ui:remove_widget" ||
                type === "ui:unregister_widget"
            ) {
                console.log("[usePluginSlots] Remove Widget:", payload);
                setSlots((prev) =>
                    prev.filter((s) => {
                        // If specific widget name is provided, only remove that one
                        if (payload.name) {
                            return !(
                                s.plugin_id === payload.plugin_id &&
                                s.name === payload.name
                            );
                        }
                        // Otherwise (e.g. plugin disabled), remove all slots for this plugin
                        return s.plugin_id !== payload.plugin_id;
                    }),
                );
            }
        };

        window.addEventListener("lumina:widget", handleWidgetEvent);

        // Polling fallback (keep it for reliability)
        const interval = setInterval(fetchSlots, 10000);

        return () => {
            clearInterval(interval);
            window.removeEventListener("lumina:widget", handleWidgetEvent);
        };
    }, [fetchSlots]);

    return { slots, fetchSlots, isLoading };
};
