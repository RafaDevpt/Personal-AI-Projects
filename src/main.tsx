// Entrada da SPA. Usa histórico por hash (#/salario) para os links diretos funcionarem
// no GitHub Pages, que não tem reescrita de rotas no servidor.
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "@tanstack/react-router";
import { getRouter } from "./router";

import "@fontsource-variable/manrope/index.css";
import "@fontsource-variable/fraunces/index.css";
import "./styles.css";

const router = getRouter();

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
