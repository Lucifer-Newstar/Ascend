// ESLint flat config: TypeScript rules + React hooks rules for the renderer and Electron code.
import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "dist-electron", "release", "node_modules"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: { globals: globals.browser },
    plugins: { "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // eslint-plugin-react-hooks 7 adds the React Compiler rules to "recommended" as errors.
      // They flag patterns that are valid React but that the compiler can't optimise (setState
      // in an effect, reading a ref during render, Date.now() in render). The app does not use
      // the compiler, so they stay visible as warnings; the classic hook rules stay errors.
      "react-hooks/set-state-in-effect": "warn",
      "react-hooks/refs": "warn",
      "react-hooks/purity": "warn",
    },
  },
  {
    files: ["electron/**/*.ts"],
    languageOptions: { globals: globals.node },
  },
  {
    // electron-builder hooks are plain CommonJS run by Node.
    files: ["build/**/*.cjs"],
    languageOptions: { globals: globals.node, sourceType: "commonjs" },
    rules: { "@typescript-eslint/no-require-imports": "off" },
  },
);
