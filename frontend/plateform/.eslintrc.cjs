module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended"
  ],
  ignorePatterns: [
    "dist",
    ".eslintrc.cjs",
    "src/components/KnowledgeBaseZh/components/@mxmweb"
  ],
  parser: "@typescript-eslint/parser",
  plugins: ["react-refresh", "import"],
  rules: {
    "no-unsafe-finally": "off",
    "no-debugger": "off",
    "no-sparse-arrays": "off",
    "no-useless-escape": "off",
    "no-unsafe-optional-chaining": "off",
    "no-undef": "off",
    "no-cond-assign": "off",
    "no-redeclare": "off",
    "no-prototype-builtins": "off",
    "react-hooks/exhaustive-deps": "off",
    "react-hooks/rules-of-hooks": "off",
    "no-case-declarations": "off",
    "no-var": "off",
    "no-empty": "off",
    "prefer-const": "off",
    "react-refresh/only-export-components": "off",
    "@typescript-eslint/ban-types": "off",
    "@typescript-eslint/ban-ts-comment": "off",
    "@typescript-eslint/no-this-alias": "off",
    // "import/no-unresolved": ["error", { caseSensitive: true }],
    // "react-refresh/only-export-components": [
    //   "warn",
    //   { allowConstantExport: true }
    // ],
    "no-unused-vars": "off",
    "no-console": "off",
    "@typescript-eslint/no-explicit-any": "off",
    "@typescript-eslint/no-unused-vars": "off",
    "@typescript-eslint/no-this-alias": [
      "error",
      {
        allowDestructuring: false,
        allowedNames: ["self", "_this"]
      }
    ]
  },
  settings: {
    "import/resolver": {
      typescript: { project: "./tsconfig.json" },
      alwaysTryTypes: true
    }
  }
};
