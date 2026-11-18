// Deixa o Node resolver imports sem extensão para ficheiros .ts (como o Vite faz), só para os testes.
// Usado com: node --experimental-strip-types --import ./tests/registar-ts.mjs --test ...
// Created by Redfox using Claude
import { register } from "node:module";

register(
  "data:text/javascript," +
    encodeURIComponent(`
export async function resolve(spec, ctx, next) {
  try { return await next(spec, ctx); }
  catch (e) {
    if ((spec.startsWith(".") || spec.startsWith("/")) && !/\\.[cm]?[jt]sx?$/.test(spec)) return next(spec + ".ts", ctx);
    throw e;
  }
}`),
);
