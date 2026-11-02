import { config } from "@repo/eslint-config/react-internal";

export default [{ ignores: ["dist/**", "src-tauri/**"] }, ...config];
