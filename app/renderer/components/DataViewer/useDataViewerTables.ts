import { useCallback, useEffect, useRef, useState } from "react";

import {
    loadTableRows,
} from "../../api/dataViewerApi";

interface UseDataViewerTablesArgs {
    isOpen: boolean;
    activeCharacterId?: string | null;
    apiBaseUrl: string;
}

export const useDataViewerTables = ({
    isOpen,
    activeCharacterId,
    apiBaseUrl,
}: UseDataViewerTablesArgs) => {
    const [selectedTable, setSelectedTable] = useState<string | null>(
        "conversation_turns",
    );
    const [tableData, setTableData] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [tableCache, setTableCache] = useState<Record<string, any[]>>({});

    const loadTableAbortRef = useRef<AbortController | null>(null);
    const isMountedRef = useRef(false);
    const selectedTableRef = useRef<string | null>("conversation_turns");
    const tableCacheRef = useRef<Record<string, any[]>>({});

    useEffect(() => {
        selectedTableRef.current = selectedTable;
    }, [selectedTable]);

    useEffect(() => {
        tableCacheRef.current = tableCache;
    }, [tableCache]);

    useEffect(() => {
        isMountedRef.current = true;

        return () => {
            isMountedRef.current = false;
            loadTableAbortRef.current?.abort();
        };
    }, []);

    const loadTableData = useCallback(
        async (tableName: string, forceRefresh: boolean = false) => {
            loadTableAbortRef.current?.abort();
            loadTableAbortRef.current = new AbortController();
            const signal = loadTableAbortRef.current.signal;

            selectedTableRef.current = tableName;
            setSelectedTable(tableName);

            const cachedRows = tableCacheRef.current[tableName];
            if (!forceRefresh && cachedRows) {
                setTableData(cachedRows);
                return;
            }

            setLoading(true);
            setTableData([]);

            try {
                const rows = await loadTableRows(
                    apiBaseUrl,
                    tableName,
                    activeCharacterId,
                    signal,
                );
                if (signal.aborted || !isMountedRef.current) {
                    return;
                }

                setTableData(rows);
                setTableCache((previous) => ({ ...previous, [tableName]: rows }));
                tableCacheRef.current = {
                    ...tableCacheRef.current,
                    [tableName]: rows,
                };
            } catch (error: any) {
                if (error?.name === "AbortError") {
                    return;
                }

                if (isMountedRef.current) {
                    console.error("Failed to load table data:", error);
                }
            } finally {
                if (!signal.aborted && isMountedRef.current) {
                    setLoading(false);
                }
            }
        },
        [activeCharacterId, apiBaseUrl],
    );

    useEffect(() => {
        if (isOpen) {
            void loadTableData(selectedTableRef.current || "conversation_turns");
        }
    }, [isOpen, loadTableData]);

    useEffect(() => {
        if (activeCharacterId) {
            setTableCache({});
            tableCacheRef.current = {};
            if (isOpen && selectedTableRef.current) {
                void loadTableData(selectedTableRef.current, true);
            }
        }
    }, [activeCharacterId, isOpen, loadTableData]);

    const refreshTable = useCallback(() => {
        if (!selectedTableRef.current) {
            return;
        }

        void loadTableData(selectedTableRef.current, true);
    }, [loadTableData]);

    return {
        selectedTable,
        setSelectedTable,
        tableData,
        loading,
        refreshTable,
        loadTableData,
    };
};
