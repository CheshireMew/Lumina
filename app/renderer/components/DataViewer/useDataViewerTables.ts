import { useCallback, useEffect, useRef, useState } from "react";

import {
    createRecord,
    deleteRecord,
    loadTableRows,
    normalizeRecordId,
    updateRecord,
} from "./dataViewerApi";

interface UseDataViewerTablesArgs {
    isOpen: boolean;
    activeCharacterId?: string | null;
    apiBaseUrl: string;
    refreshGraph: () => Promise<void> | void;
}

export const useDataViewerTables = ({
    isOpen,
    activeCharacterId,
    apiBaseUrl,
    refreshGraph,
}: UseDataViewerTablesArgs) => {
    const [selectedTable, setSelectedTable] = useState<string | null>(
        "conversation_log",
    );
    const [tableData, setTableData] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [tableCache, setTableCache] = useState<Record<string, any[]>>({});

    const [editingRecord, setEditingRecord] = useState<any>(null);
    const [isCreating, setIsCreating] = useState(false);
    const [editorForm, setEditorForm] = useState<any>({});

    const loadTableAbortRef = useRef<AbortController | null>(null);
    const isMountedRef = useRef(false);
    const selectedTableRef = useRef<string | null>("conversation_log");
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

            if (tableName === "knowledge_facts") {
                setLoading(false);
                setTableData([]);
                await refreshGraph();
                return;
            }

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
        [activeCharacterId, apiBaseUrl, refreshGraph],
    );

    useEffect(() => {
        if (isOpen) {
            void loadTableData(selectedTableRef.current || "conversation_log");
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

    const handleEditRecord = useCallback((record: any) => {
        setEditingRecord(record);
        setIsCreating(false);
        setEditorForm(JSON.parse(JSON.stringify(record)));
    }, []);

    const handleCreateRecord = useCallback(() => {
        setEditingRecord({});
        setIsCreating(true);

        const nextForm: Record<string, any> = {};
        if (tableData.length > 0) {
            Object.keys(tableData[0]).forEach((column) => {
                if (column !== "id" && column !== "created_at") {
                    nextForm[column] = "";
                }
            });
        }

        setEditorForm(nextForm);
    }, [tableData]);

    const handleDeleteRecord = useCallback(
        async (idOfRow: any) => {
            const rawId = normalizeRecordId(idOfRow);

            if (
                !confirm(`Are you sure you want to delete this record?\nID: ${rawId}`)
            ) {
                return;
            }

            if (!selectedTable) {
                return;
            }

            try {
                await deleteRecord(apiBaseUrl, selectedTable, rawId);
                setTableData((previous) =>
                    previous.filter((row) => normalizeRecordId(row.id) !== rawId),
                );
            } catch (error) {
                alert(`Delete failed: ${error}`);
            }
        },
        [apiBaseUrl, selectedTable],
    );

    const handleSaveRecord = useCallback(async () => {
        if (!selectedTable) {
            return;
        }

        try {
            if (!isCreating) {
                const recordId = normalizeRecordId(editingRecord?.id);
                const { id: _, ...updateData } = editorForm;
                await updateRecord(apiBaseUrl, selectedTable, recordId, updateData);
                setEditingRecord(null);
                setTableData((previous) =>
                    previous.map((row) =>
                        normalizeRecordId(row.id) === recordId
                            ? { ...row, ...updateData }
                            : row,
                    ),
                );
                return;
            }

            await createRecord(apiBaseUrl, selectedTable, editorForm);
            setEditingRecord(null);
            void loadTableData(selectedTable, true);
        } catch (error) {
            alert(`Error saving: ${error}`);
        }
    }, [apiBaseUrl, editorForm, editingRecord, isCreating, loadTableData, selectedTable]);

    const closeEditor = useCallback(() => {
        setEditingRecord(null);
    }, []);

    return {
        selectedTable,
        setSelectedTable,
        tableData,
        loading,
        refreshTable,
        loadTableData,
        handleEditRecord,
        handleCreateRecord,
        handleDeleteRecord,
        editingRecord,
        isCreating,
        editorForm,
        setEditorForm,
        handleSaveRecord,
        closeEditor,
    };
};
