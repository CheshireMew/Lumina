import { useCallback, useEffect, useRef, useState } from "react";

import {
    createRecord,
    deleteRecord,
    loadTableRows,
    normalizeRecordId,
    updateRecord,
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

    const [editingRecord, setEditingRecord] = useState<any>(null);
    const [isCreating, setIsCreating] = useState(false);
    const [editorForm, setEditorForm] = useState<any>({});
    const [editorSaving, setEditorSaving] = useState(false);

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

    const handleEditRecord = useCallback((record: any) => {
        setEditingRecord(record);
        setIsCreating(false);
        setEditorForm(JSON.parse(JSON.stringify(record)));
    }, []);

    const handleCreateRecord = useCallback(() => {
        setEditingRecord({});
        setIsCreating(true);

        const nextForm: Record<string, any> = {};
        const hiddenCreateColumns = new Set([
            "id",
            "created_at",
            "updated_at",
            "embedding",
            "vector",
            "metadata",
        ]);

        if (tableData.length > 0) {
            Object.keys(tableData[0]).forEach((column) => {
                if (!hiddenCreateColumns.has(column)) {
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
                const removeDeleted = (rows: any[]) =>
                    rows.filter((row) => normalizeRecordId(row.id) !== rawId);
                setTableData(removeDeleted);
                setTableCache((previous) => {
                    const cachedRows = previous[selectedTable] || tableData;
                    const next = {
                        ...previous,
                        [selectedTable]: removeDeleted(cachedRows),
                    };
                    tableCacheRef.current = next;
                    return next;
                });
            } catch (error) {
                alert(`Delete failed: ${error}`);
            }
        },
        [apiBaseUrl, selectedTable, tableData],
    );

    const handleSaveRecord = useCallback(async () => {
        if (!selectedTable) {
            return;
        }

        setEditorSaving(true);
        try {
            if (!isCreating) {
                const recordId = normalizeRecordId(editingRecord?.id);
                const { id: _, ...updateData } = editorForm;
                await updateRecord(apiBaseUrl, selectedTable, recordId, updateData);
                setEditingRecord(null);
                const applyUpdate = (rows: any[]) =>
                    rows.map((row) =>
                        normalizeRecordId(row.id) === recordId
                            ? { ...row, ...updateData }
                            : row,
                    );
                setTableData(applyUpdate);
                setTableCache((previous) => {
                    const cachedRows = previous[selectedTable] || tableData;
                    const next = {
                        ...previous,
                        [selectedTable]: applyUpdate(cachedRows),
                    };
                    tableCacheRef.current = next;
                    return next;
                });
                return;
            }

            await createRecord(apiBaseUrl, selectedTable, editorForm);
            setEditingRecord(null);
            void loadTableData(selectedTable, true);
        } catch (error) {
            alert(`Error saving: ${error}`);
        } finally {
            setEditorSaving(false);
        }
    }, [apiBaseUrl, editorForm, editingRecord, isCreating, loadTableData, selectedTable, tableData]);

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
        editorSaving,
        setEditorForm,
        handleSaveRecord,
        closeEditor,
    };
};
