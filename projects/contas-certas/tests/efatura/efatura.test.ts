/**
 * Testes de regressão da leitura de capturas do e-fatura (leitura por posição).
 *
 * As fixtures são palavras com caixa produzidas pelo tesseract 5 a partir de capturas SINTÉTICAS da página
 * «Deduções Provisórias em IRS», com dados fictícios (ver tests/efatura/gerar). Cada fixture tem uma ou duas
 * leituras, como a aplicação faz no browser (tamanho original e, se a letra for pequena, ampliada).
 *
 * A regra mais importante: um valor errado SEM aviso nunca passa. Um valor não lido é aceitável
 * (a pessoa escreve-o à mão); um valor errado e calado é o que estragava o preenchimento.
 * Created by Redfox using Claude
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { juntarLeituras, parseEfaturaPosicional, type Palavra } from "../../src/lib/import/efaturaPosicional.ts";
import type { CampoEfatura, EfaturaLido } from "../../src/lib/import/efatura.ts";

const dir = new URL("./fixtures/", import.meta.url);
const NOMES: Record<string, CampoEfatura> = {
  "Despesas Gerais Familiares": "gerais", "Saúde": "saude", "Educação": "educacao", "Habitação": "habitacao", "Lares": "lares",
  "Reparação de Automóveis": "reparacao_automoveis", "Restauração e Alojamento": "restauracao_alojamento", "Cabeleireiros": "cabeleireiros",
  "Atividades Veterinárias": "veterinarios", "Transportes Públicos Coletivos": "transportes_publicos", "Ginásios": "ginasios",
};
const esperado = new Map<CampoEfatura, number>(
  Object.entries(JSON.parse(readFileSync(new URL("esperado.json", dir), "utf8")) as Record<string, number>).map(([k, v]) => [NOMES[k]!, v]),
);

function ler(nome: string): EfaturaLido {
  const leituras = JSON.parse(readFileSync(new URL(`${nome}.json`, dir), "utf8")) as Palavra[][];
  const lidas = leituras.map(parseEfaturaPosicional).filter((r): r is EfaturaLido => !("erro" in r));
  const r = juntarLeituras(lidas);
  assert.ok(r, `${nome}: nenhuma leitura`);
  return r;
}

/** [fixture, mínimo de valores certos] */
const CASOS: [string, number][] = [
  ["pc_claro", 11], ["pc_escuro", 11], ["pc_B", 11], ["pc_C", 11], ["pc_pequeno", 11],
  ["tlm_claro", 11], ["tlm_escuro", 11], ["tlm_1col", 11], ["pdf", 11],
  ["pc_cortado", 8], // só se veem duas filas de mosaicos
  ["pc_jpeg", 2], // JPEG a 30%, desfocado e reduzido: lê pouco, mas não pode inventar
];

for (const [nome, minimo] of CASOS) {
  test(`${nome}: nenhum valor errado sem aviso, pelo menos ${minimo} certos`, () => {
    const r = ler(nome);
    let certos = 0;
    for (const v of r.valores) {
      const e = esperado.get(v.campo);
      assert.notEqual(e, undefined, `${nome}: campo inesperado ${v.campo}`);
      if (Math.abs(v.valor - e!) < 0.005) certos++;
      else assert.ok(v.duvida, `${nome}: ${v.campo}=${v.valor} (esperado ${e}) e sem aviso`);
    }
    assert.ok(certos >= minimo, `${nome}: ${certos} certos, esperados pelo menos ${minimo}`);
  });
}

test("valores certos não levantam falsos alarmes nas capturas limpas", () => {
  for (const nome of ["pc_claro", "pc_escuro", "pc_B", "pc_C", "tlm_claro", "tlm_escuro", "pdf"]) {
    const alarmes = ler(nome).valores.filter((v) => v.duvida && Math.abs(v.valor - esperado.get(v.campo)!) < 0.005);
    assert.deepEqual(alarmes.map((v) => v.campo), [], `${nome}: falsos alarmes`);
  }
});

test("o total vem do «Total», não de um mosaico", () => {
  for (const nome of ["pc_claro", "tlm_claro", "pdf"]) assert.equal(ler(nome).total, 1308.3);
});

test("menu lateral e notas de rodapé com «Saúde» não roubam valores", () => {
  // Palavras mínimas: menu «Saúde» à esquerda na mesma fila de «Total: 99,00 €»; mosaico Saúde com dedução.
  const p = (text: string, x0: number, y0: number, w = text.length * 9): Palavra => ({ text, x0, y0, x1: x0 + w, y1: y0 + 18 });
  const r = parseEfaturaPosicional([
    p("Saúde", 10, 100), p("Total:", 200, 98), p("99,00", 260, 98), p("€", 310, 98),
    p("Saúde", 200, 200), p("Dedução", 200, 240), p("12,34", 290, 240), p("€", 340, 240),
    p("As", 200, 400), p("despesas", 225, 400), p("de", 305, 400), p("saúde", 330, 400), p("com", 385, 400), p("IVA", 420, 400),
    p("à", 455, 400), p("taxa", 470, 400), p("normal", 510, 400), p("são", 570, 400), p("consideradas", 605, 400), p("15,00", 720, 400),
  ]);
  assert.ok(!("erro" in r));
  assert.deepEqual(r.valores.map((v) => [v.campo, v.valor]), [["saude", 12.34]]);
  assert.equal(r.total, 99);
});

test("um valor acima do máximo legal é assinalado", () => {
  const p = (text: string, x0: number, y0: number): Palavra => ({ text, x0, y0, x1: x0 + text.length * 9, y1: y0 + 18 });
  const r = parseEfaturaPosicional([p("Despesas", 10, 10), p("Gerais", 95, 10), p("Familiares", 155, 10), p("Dedução", 10, 40), p("950,00", 90, 40), p("€", 150, 40)]);
  assert.ok(!("erro" in r));
  assert.match(r.valores[0]?.duvida ?? "", /máximo legal/);
});
