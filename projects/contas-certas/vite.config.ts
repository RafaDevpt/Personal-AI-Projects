// Build estático (SPA) para o GitHub Pages.
// A versão original no Lovable usa TanStack Start com SSR; aqui tudo corre no browser,
// por isso basta o Vite + React + Tailwind. Base relativa ("./") para funcionar em qualquer
// subpasta (ex.: .../Personal-AI-Projects/contas-certas/); as rotas usam #/ por isso há só um index.html.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  base: process.env.BASE ?? "./",
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
    dedupe: ["react", "react-dom", "@tanstack/react-router"],
  },
  build: { outDir: "dist", sourcemap: false },
});
