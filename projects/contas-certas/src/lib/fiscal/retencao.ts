import { euroInferior } from "./money";
import { NOVEMBRO_FATOR, TABELAS_RETENCAO, type TabelaRetencao } from "./rules2026";

export type Situacao = "nao_casado" | "casado_dois" | "casado_unico";

export function escolherTabela(situacao: Situacao, dependentes: number): TabelaRetencao {
  if (situacao === "casado_unico") return "III";
  if (situacao === "nao_casado" && dependentes >= 1) return "II";
  return "I";
}

export interface RetencaoDetalhe {
  tabela: TabelaRetencao;
  R: number;
  taxa: number;
  parcela: number;
  parcelaDependentes: number;
  retencao: number;
  novembroAplicado: boolean;
}

export function calcRetencao(
  R: number,
  tabela: TabelaRetencao,
  dependentes = 0,
  depDeficiencia = 0,
  novembro = false,
  /** Parte do rendimento sujeita a retenção (IRS Jovem: parte não isenta ÷ total — art. 99.º-F n.º 4 CIRS). */
  fracaoSujeita = 1,
): RetencaoDetalhe {
  const def = TABELAS_RETENCAO[tabela];
  const base = Math.max(0, R);
  const linha = def.linhas.find((l) => base <= l.ate) ?? def.linhas[def.linhas.length - 1]!;
  const parcela =
    typeof linha.parcela === "number"
      ? linha.parcela
      : linha.taxa * linha.parcela.coef * (linha.parcela.ref - base);
  const parcelaDependentes =
    linha.taxa > 0 ? def.porDependente * dependentes + def.porDependenteDeficiencia * depDeficiencia : 0;
  const novembroAplicado = novembro && base <= def.limiteNovembro;
  const valor = Math.max(0, base * linha.taxa - parcela - parcelaDependentes) * fracaoSujeita * (novembroAplicado ? NOVEMBRO_FATOR : 1);
  const retencao = euroInferior(valor);
  return { tabela, R: base, taxa: linha.taxa, parcela, parcelaDependentes, retencao, novembroAplicado };
}
