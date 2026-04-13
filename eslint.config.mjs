import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
    {
        ignores: [
            "automation/**",
            "python_backend/**",
            "dist/**",
            "dist-electron/**",
            "dist_backend/**",
            "release/**",
            "logs/**",
            "models/**",
            "public/**",
            "assets/**",
            "GPT-SoVITS/**",
            "Lumina_Data/**",
            "node_modules/**",
        ],
    },
    {
        files: ["app/**/*.{ts,tsx}", "core/**/*.{ts,tsx}", "vite.config.mts"],
        languageOptions: {
            parser: tseslint.parser,
            ecmaVersion: "latest",
            sourceType: "module",
            globals: {
                ...globals.browser,
                ...globals.node,
            },
        },
        plugins: {
            "@typescript-eslint": tseslint.plugin,
        },
        rules: {
            "constructor-super": "error",
            "no-constant-condition": ["error", { checkLoops: false }],
            "no-debugger": "error",
            "no-empty-pattern": "error",
            "no-unreachable": "error",
            "no-unsafe-finally": "error",
            "@typescript-eslint/no-explicit-any": "off",
            "@typescript-eslint/no-unused-vars": "off",
        },
    },
);
