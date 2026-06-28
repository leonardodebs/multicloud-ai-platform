// Configuração mínima do ESLint para React (usada no CI).
module.exports = {
  root: true,
  env: { browser: true, es2021: true, node: true },
  extends: ["eslint:recommended", "plugin:react/recommended"],
  parserOptions: { ecmaVersion: "latest", sourceType: "module" },
  settings: { react: { version: "detect" } },
  rules: {
    // Com React 17+ não é preciso importar React em todo arquivo JSX.
    "react/react-in-jsx-scope": "off",
    "react/prop-types": "off",
  },
};
