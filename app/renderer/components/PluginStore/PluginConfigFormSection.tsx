import React from "react";

import GalgameSelect from "./GalgameSelect";

interface PluginConfigFormSectionProps {
    plugin: any;
    hasLlmRoutes: boolean;
    schema: any;
    values: Record<string, any>;
    setValues: React.Dispatch<React.SetStateAction<Record<string, any>>>;
}

export const PluginConfigFormSection: React.FC<PluginConfigFormSectionProps> = ({
    plugin,
    hasLlmRoutes,
    schema,
    values,
    setValues,
}) => {
    if (!schema) {
        return hasLlmRoutes ? null : (
            <div
                className="no-config-message"
                style={{ marginBottom: "20px", fontStyle: "italic", color: "#888" }}
            >
                No standard configuration available for this plugin.
            </div>
        );
    }

    if (schema.fields) {
        return (
            <>
                {schema.fields.map((field: any) => {
                    const fieldValue =
                        values[field.key] !== undefined
                            ? values[field.key]
                            : plugin.current_config?.[field.key] ?? field.default ?? "";

                    return (
                        <div key={field.key} className="form-group">
                            <label>{field.label}</label>
                            {field.type === "select" ? (
                                <GalgameSelect
                                    value={fieldValue}
                                    options={field.options}
                                    onChange={(value) =>
                                        setValues((previous) => ({
                                            ...previous,
                                            [field.key]: value,
                                        }))
                                    }
                                />
                            ) : (
                                <input
                                    type={field.type === "number" ? "number" : "text"}
                                    className="galgame-input"
                                    value={fieldValue}
                                    onChange={(event) => {
                                        const nextValue =
                                            field.type === "number"
                                                ? Number(event.target.value)
                                                : event.target.value;
                                        setValues((previous) => ({
                                            ...previous,
                                            [field.key]: nextValue,
                                        }));
                                    }}
                                />
                            )}
                        </div>
                    );
                })}
            </>
        );
    }

    const currentValue =
        values[schema.key] !== undefined
            ? values[schema.key]
            : plugin.current_config?.[schema.key] ?? "";

    return (
        <div className="form-group">
            <label>{schema.label}</label>

            {schema.type === "select" && schema.options ? (
                <GalgameSelect
                    value={currentValue}
                    options={schema.options}
                    onChange={(value) => setValues({ ...values, [schema.key]: value })}
                />
            ) : (
                <input
                    type={schema.type === "number" ? "number" : "text"}
                    className="galgame-input"
                    value={currentValue}
                    onChange={(event) =>
                        setValues({ ...values, [schema.key]: event.target.value })
                    }
                    step={schema.type === "number" ? "0.1" : undefined}
                />
            )}
        </div>
    );
};
