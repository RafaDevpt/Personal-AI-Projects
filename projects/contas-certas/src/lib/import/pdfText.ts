/**
 * PDF → texto simples, inteiramente no browser (o ficheiro nunca sai do dispositivo).
 * Este módulo só deve ser carregado com import() dinâmico quando o utilizador escolhe um ficheiro.
 * Usa a build "legacy" do pdf.js (compatível com telemóveis mais antigos) e o worker local via `?url`.
 */
import * as pdfjs from "pdfjs-dist/legacy/build/pdf.mjs";
import workerUrl from "pdfjs-dist/legacy/build/pdf.worker.min.mjs?url";

import type { Palavra } from "./efaturaPosicional";

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

interface Pedaco {
  str: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

/** Junta os pedaços de texto por linha (posição y), da esquerda para a direita. */
function juntarLinhas(pedacos: Pedaco[]): string[] {
  const ordenados = [...pedacos].sort((a, b) => b.y - a.y || a.x - b.x);
  const linhas: Pedaco[][] = [];
  for (const p of ordenados) {
    const ultima = linhas[linhas.length - 1];
    const tol = Math.max(2, (p.h || 10) * 0.5);
    if (ultima && Math.abs(ultima[0]!.y - p.y) <= tol) ultima.push(p);
    else linhas.push([p]);
  }
  return linhas.map((l) => {
    l.sort((a, b) => a.x - b.x);
    let out = "";
    let fim = -Infinity;
    for (const p of l) {
      if (out && p.x - fim > Math.max(1, (p.h || 10) * 0.15) && !out.endsWith(" ") && !p.str.startsWith(" ")) out += " ";
      out += p.str;
      fim = p.x + p.w;
    }
    return out.replace(/\s+/g, " ").trim();
  });
}

export async function extrairTextoPdf(ficheiro: File | ArrayBuffer): Promise<string> {
  const dados = ficheiro instanceof ArrayBuffer ? ficheiro : await ficheiro.arrayBuffer();
  const tarefa = pdfjs.getDocument({ data: new Uint8Array(dados) });
  const doc = await tarefa.promise;
  try {
    const paginas: string[] = [];
    for (let n = 1; n <= doc.numPages; n++) {
      const pagina = await doc.getPage(n);
      const conteudo = await pagina.getTextContent();
      const pedacos: Pedaco[] = [];
      for (const item of conteudo.items) {
        if (!("str" in item) || !item.str) continue;
        const t = item.transform as number[];
        pedacos.push({ str: item.str, x: t[4] ?? 0, y: t[5] ?? 0, w: item.width, h: item.height || Math.abs(t[3] ?? 0) });
      }
      paginas.push(juntarLinhas(pedacos).filter(Boolean).join("\n"));
    }
    return paginas.filter(Boolean).join("\n");
  } finally {
    await tarefa.destroy();
  }
}

/**
 * PDF → pedaços de texto com caixa, em coordenadas de ecrã (y a crescer para baixo), com as páginas
 * empilhadas umas por baixo das outras. Serve a leitura por posição dos mosaicos do e-fatura.
 */
export async function extrairPalavrasPdf(ficheiro: File | ArrayBuffer): Promise<Palavra[]> {
  const dados = ficheiro instanceof ArrayBuffer ? ficheiro : await ficheiro.arrayBuffer();
  const tarefa = pdfjs.getDocument({ data: new Uint8Array(dados) });
  const doc = await tarefa.promise;
  try {
    const out: Palavra[] = [];
    let deslocamento = 0;
    for (let n = 1; n <= doc.numPages; n++) {
      const pagina = await doc.getPage(n);
      const altura = pagina.getViewport({ scale: 1 }).height;
      const conteudo = await pagina.getTextContent();
      for (const item of conteudo.items) {
        if (!("str" in item) || !item.str.trim()) continue;
        const t = item.transform as number[];
        const h = item.height || Math.abs(t[3] ?? 0) || 10;
        const x = t[4] ?? 0;
        const yBase = altura - (t[5] ?? 0);
        out.push({ text: item.str, x0: x, x1: x + item.width, y0: deslocamento + yBase - h, y1: deslocamento + yBase });
      }
      deslocamento += altura + 20;
    }
    return out;
  } finally {
    await tarefa.destroy();
  }
}
