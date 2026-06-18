import { useCallback, useEffect, useRef, useState } from "react";

import { loadGraphData } from "./dataViewerApi";

interface UseDataViewerGraphArgs {
    isOpen: boolean;
    activeTab: "tables" | "query" | "stats" | "graph";
    activeCharacterId?: string | null;
    apiBaseUrl: string;
}

export const useDataViewerGraph = ({
    isOpen,
    activeTab,
    activeCharacterId,
    apiBaseUrl,
}: UseDataViewerGraphArgs) => {
    const [graphData, setGraphData] = useState<{
        nodes: any[];
        edges: any[];
    } | null>(null);
    const [selectedNode, setSelectedNode] = useState<any>(null);
    const [detailEdge, setDetailEdge] = useState<any>(null);
    const [loading, setLoading] = useState(false);

    const loadGraphAbortRef = useRef<AbortController | null>(null);
    const isMountedRef = useRef(false);

    useEffect(() => {
        isMountedRef.current = true;

        return () => {
            isMountedRef.current = false;
            loadGraphAbortRef.current?.abort();
        };
    }, []);

    const loadGraph = useCallback(async () => {
        loadGraphAbortRef.current?.abort();
        loadGraphAbortRef.current = new AbortController();
        const signal = loadGraphAbortRef.current.signal;

        setLoading(true);

        try {
            const nextGraph = await loadGraphData(
                apiBaseUrl,
                activeCharacterId,
                signal,
            );
            if (signal.aborted || !isMountedRef.current) {
                return;
            }

            setGraphData(nextGraph);
        } catch (error: any) {
            if (error?.name === "AbortError") {
                return;
            }
            console.error("Graph load failed:", error);
        } finally {
            if (!signal.aborted && isMountedRef.current) {
                setLoading(false);
            }
        }
    }, [activeCharacterId, apiBaseUrl]);

    useEffect(() => {
        if (isOpen && activeTab === "graph") {
            void loadGraph();
        }
    }, [activeTab, isOpen, loadGraph]);

    useEffect(() => {
        if (activeCharacterId) {
            setGraphData(null);
            setSelectedNode(null);
            setDetailEdge(null);
            if (isOpen && activeTab === "graph") {
                void loadGraph();
            }
        }
    }, [activeCharacterId, activeTab, isOpen, loadGraph]);

    return {
        graphData,
        selectedNode,
        detailEdge,
        loading,
        loadGraph,
        setSelectedNode,
        setDetailEdge,
    };
};

