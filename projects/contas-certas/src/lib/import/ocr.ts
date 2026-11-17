/**
 * Imagem → texto, inteiramente no browser (a imagem nunca sai do dispositivo).
 * Só deve ser carregado com import() dinâmico quando a pessoa escolhe uma imagem.
 * O worker, o motor e os dados da língua são servidos pelo próprio site (public/ocr), sem CDN.
 * Os caminhos são convertidos em URLs absolutos (a partir da página atual) para funcionarem numa
 * subpasta do GitHub Pages e dentro do worker, que resolve caminhos relativos a partir de si próprio.
 */
import { createWorker } from "tesseract.js";

const abs = (p: string) => new URL(`${import.meta.env.BASE_URL}${p}`, document.baseURI).href;

export async function extrairTextoImagem(ficheiro: File): Promise<string> {
  const worker = await createWorker("por", 1, {
    workerPath: abs("ocr/worker.min.js"),
    corePath: abs("ocr/core"),
    langPath: abs("ocr/lang"),
    workerBlobURL: false,
    gzip: true,
  });
  try {
    const { data } = await worker.recognize(ficheiro);
    return data.text;
  } finally {
    await worker.terminate();
  }
}
