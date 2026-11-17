// Copia o motor de OCR (tesseract.js) para public/ocr, para ser servido pelo próprio site, sem CDN em runtime.
// Os dados da língua portuguesa são descarregados uma vez no build (GitHub Actions).
// Created by Redfox using Claude
import { cpSync, existsSync, mkdirSync, readdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const out = "public/ocr";
mkdirSync(join(out, "core"), { recursive: true });
mkdirSync(join(out, "lang"), { recursive: true });

// Worker do tesseract.js
cpSync("node_modules/tesseract.js/dist/worker.min.js", join(out, "worker.min.js"));

// Motores WASM (todas as variantes; o worker escolhe a que o browser suporta)
const coreDir = "node_modules/tesseract.js-core";
const cores = readdirSync(coreDir).filter((f) => /^tesseract-core.*\.wasm\.js$/.test(f));
if (!cores.length) throw new Error("Não encontrei os ficheiros tesseract-core*.wasm.js");
for (const f of cores) cpSync(join(coreDir, f), join(out, "core", f));
console.log(`OCR: ${cores.length} motores copiados`);

// Dados da língua (por.traineddata.gz)
const lang = join(out, "lang", "por.traineddata.gz");
if (!existsSync(lang)) {
  const url = "https://cdn.jsdelivr.net/npm/@tesseract.js-data/por/4.0.0_best_int/por.traineddata.gz";
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Falhou o download de ${url}: ${res.status}`);
  writeFileSync(lang, Buffer.from(await res.arrayBuffer()));
  console.log("OCR: dados da língua portuguesa descarregados");
}
