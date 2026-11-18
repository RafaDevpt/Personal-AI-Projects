/**
 * Imagem → palavras com posição, inteiramente no browser (a imagem nunca sai do dispositivo).
 * Só deve ser carregado com import() dinâmico quando a pessoa escolhe uma imagem.
 * O worker, o motor e os dados da língua são servidos pelo próprio site (public/ocr), sem CDN.
 * Os caminhos são convertidos em URLs absolutos (a partir da página atual) para funcionarem numa
 * subpasta do GitHub Pages e dentro do worker, que resolve caminhos relativos a partir de si próprio.
 *
 * Porque é que isto não é só "recognize(ficheiro)":
 *  - O modo por omissão do tesseract.js (SINGLE_BLOCK) trata a captura como um parágrafo único e cola
 *    as colunas da grelha de mosaicos. Aqui usa-se SPARSE_TEXT, que encontra cada pedaço de texto
 *    onde ele está, e guarda-se a caixa de cada palavra para ligar valores a categorias por posição.
 *  - Capturas em modo escuro, com pouco contraste ou com letra pequena leem-se mal. A imagem passa a
 *    cinzento, é invertida se o fundo for escuro, o contraste é esticado e, se a letra for pequena,
 *    faz-se uma segunda leitura ampliada.
 * Created by Redfox using Claude
 */
import { createWorker, PSM, type Block } from "tesseract.js";
import type { Palavra } from "./efaturaPosicional";

const abs = (p: string) => new URL(`${import.meta.env.BASE_URL}${p}`, document.baseURI).href;

/** Altura (px) abaixo da qual a letra é considerada pequena e se faz uma leitura ampliada. */
const LETRA_PEQUENA = 16;
/** Altura alvo da letra na leitura ampliada. */
const LETRA_ALVO = 26;
/** Lado máximo da imagem processada, para não esgotar a memória em telemóveis. */
const LADO_MAX = 4200;

/** Desenha a imagem em cinzento, invertida se o fundo for escuro, com o contraste esticado. */
function prepararImagem(img: ImageBitmap, escala: number): HTMLCanvasElement {
  const f = Math.min(escala, LADO_MAX / Math.max(img.width, img.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(img.width * f));
  canvas.height = Math.max(1, Math.round(img.height * f));
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) throw new Error("Canvas 2D indisponível");
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
  const dados = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const px = dados.data;
  const n = px.length / 4;
  const cinza = new Uint8ClampedArray(n);
  const hist = new Uint32Array(256);
  let soma = 0;
  for (let i = 0; i < n; i++) {
    const g = Math.round(0.299 * px[i * 4]! + 0.587 * px[i * 4 + 1]! + 0.114 * px[i * 4 + 2]!);
    cinza[i] = g;
    hist[g]!++;
    soma += g;
  }
  const inverter = soma / n < 128;
  // Esticar o contraste entre os percentis 2 e 98 (ignora pixéis isolados muito claros ou escuros).
  const corte = n * 0.02;
  let lo = 0, hi = 255, acc = 0;
  for (let v = 0; v < 256; v++) { acc += hist[v]!; if (acc > corte) { lo = v; break; } }
  acc = 0;
  for (let v = 255; v >= 0; v--) { acc += hist[v]!; if (acc > corte) { hi = v; break; } }
  const amp = Math.max(1, hi - lo);
  for (let i = 0; i < n; i++) {
    let g = ((cinza[i]! - lo) * 255) / amp;
    if (inverter) g = 255 - g;
    px[i * 4] = px[i * 4 + 1] = px[i * 4 + 2] = g;
    px[i * 4 + 3] = 255;
  }
  ctx.putImageData(dados, 0, 0);
  return canvas;
}

function palavrasDosBlocos(blocos: Block[] | null | undefined): Palavra[] {
  const out: Palavra[] = [];
  for (const b of blocos ?? [])
    for (const p of b.paragraphs)
      for (const l of p.lines)
        for (const w of l.words) if (w.text.trim()) out.push({ text: w.text, ...w.bbox });
  return out;
}

const mediana = (xs: number[]) => { const s = [...xs].sort((a, b) => a - b); return s[Math.floor(s.length / 2)] ?? 0; };

/**
 * Lê a imagem e devolve uma ou duas listas de palavras (tamanho original e, se a letra for pequena,
 * ampliada). As coordenadas de cada lista estão na escala da respetiva leitura.
 */
export async function lerPalavrasImagem(ficheiro: File): Promise<Palavra[][]> {
  const img = await createImageBitmap(ficheiro);
  const worker = await createWorker("por", 1, {
    workerPath: abs("ocr/worker.min.js"),
    corePath: abs("ocr/core"),
    langPath: abs("ocr/lang"),
    workerBlobURL: false,
    gzip: true,
  });
  try {
    await worker.setParameters({ tessedit_pageseg_mode: PSM.SPARSE_TEXT, user_defined_dpi: "300" });
    const ler = async (canvas: HTMLCanvasElement) => palavrasDosBlocos((await worker.recognize(canvas, {}, { blocks: true })).data.blocks);
    const primeira = await ler(prepararImagem(img, 1));
    const leituras = [primeira];
    const h = mediana(primeira.map((p) => p.y1 - p.y0));
    if (primeira.length === 0 || h < LETRA_PEQUENA) {
      const escala = Math.min(3, LETRA_ALVO / Math.max(h, 8));
      leituras.push(await ler(prepararImagem(img, escala)));
    }
    return leituras;
  } finally {
    img.close();
    await worker.terminate();
  }
}
