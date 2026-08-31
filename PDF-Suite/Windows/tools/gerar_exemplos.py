"""
PT-PT: Gerador de ficheiros de exemplo.

       Cria um formulario em papel e seis propostas de fornecedores para se
       poder experimentar a aplicacao sem ter de arranjar documentos reais — e
       sem os pôr num repositorio, que e o ponto: propostas verdadeiras trazem
       precos, contactos e condicoes comerciais que nao devem sair da empresa.

       Correr com:  python tools/gerar_exemplos.py exemplos/

EN-UK: Sample file generator.

       Creates a paper form and six vendor quotes so the application can be
       tried without finding real documents — and without putting them in a
       repository, which is the point: real quotes carry prices, contacts and
       commercial terms that should not leave the company.

Created by Redfox using Claude
"""

from __future__ import annotations

import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

LARGURA, ALTURA = A4


def formulario(destino: Path) -> None:
    """PT-PT: Formulario em papel, sem campos. / EN-UK: A paper form, no fields."""
    c = canvas.Canvas(str(destino), pagesize=A4)

    c.setFont("Helvetica-Bold", 15)
    c.drawString(25 * mm, ALTURA - 28 * mm, "PEDIDO DE ACESSO A SISTEMAS")
    c.setFont("Helvetica", 9)
    c.drawString(25 * mm, ALTURA - 34 * mm, "Preencher a tinta azul ou preta e entregar no departamento de IT")

    y = ALTURA - 50 * mm
    c.setFont("Helvetica", 10)

    # PT-PT: Campos com linha desenhada.
    for etiqueta, largura in (
        ("Nome completo:", 110),
        ("Número de colaborador:", 60),
        ("Departamento:", 90),
        ("Função:", 90),
        ("Data de início:", 45),
        ("Chefia directa:", 100),
    ):
        c.drawString(25 * mm, y, etiqueta)
        x = 25 * mm + c.stringWidth(etiqueta, "Helvetica", 10) + 6
        c.setLineWidth(0.5)
        c.line(x, y - 2, x + largura * mm * 0.35 + 40, y - 2)
        y -= 11 * mm

    # PT-PT: Campos com sublinhados escritos.
    y -= 4 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(25 * mm, y, "Contactos")
    y -= 9 * mm
    c.setFont("Helvetica", 10)
    c.drawString(25 * mm, y, "Email: ________________________________")
    c.drawString(115 * mm, y, "Extensão: ____________")
    y -= 11 * mm

    # PT-PT: Caixas de seleccao.
    c.setFont("Helvetica-Bold", 11)
    c.drawString(25 * mm, y, "Sistemas a atribuir")
    y -= 9 * mm
    c.setFont("Helvetica", 10)

    for indice, sistema in enumerate(
        ["Opera PMS", "Simphony POS", "Microsoft 365", "VPN", "Impressoras", "Partilhas de rede"]
    ):
        coluna = indice % 2
        if coluna == 0 and indice:
            y -= 8 * mm
        x = 25 * mm + coluna * 80 * mm
        c.rect(x, y - 2, 9, 9)
        c.drawString(x + 14, y, sistema)

    y -= 16 * mm

    # PT-PT: Caixa de texto de varias linhas.
    c.setFont("Helvetica", 10)
    c.drawString(25 * mm, y, "Observações:")
    y -= 4 * mm
    c.rect(25 * mm, y - 26 * mm, 160 * mm, 26 * mm)
    y -= 36 * mm

    # PT-PT: Assinaturas.
    c.line(25 * mm, y, 90 * mm, y)
    c.line(110 * mm, y, 175 * mm, y)
    c.setFont("Helvetica", 8)
    c.drawString(25 * mm, y - 5 * mm, "Assinatura do colaborador")
    c.drawString(110 * mm, y - 5 * mm, "Assinatura da chefia")

    c.setFont("Helvetica-Oblique", 7)
    c.drawString(25 * mm, 15 * mm, "Documento de exemplo gerado para testes. Created by Redfox using Claude.")
    c.showPage()
    c.save()


PROPOSTAS = [
    {
        "ficheiro": "proposta_alfa.pdf",
        "fornecedor": "Alfa Sistemas, Lda.",
        "ref": "PROP-2026-0141",
        "linhas": [
            ("Switch 48 portas PoE+", "4", "1.180,00", "4.720,00"),
            ("Access point Wi-Fi 6", "12", "245,00", "2.940,00"),
            ("Instalação e configuração", "1", "1.850,00", "1.850,00"),
        ],
        "total": "9.510,00",
        "iva": "acresce IVA à taxa legal de 23%",
        "pagamento": "Condições de pagamento: 30 dias após factura.",
        "entrega": "Prazo de entrega: 15 dias úteis após adjudicação.",
        "garantia": "Garantia: 36 meses on-site.",
        "validade": "Proposta válida por 30 dias.",
    },
    {
        "ficheiro": "proposta_beta.pdf",
        "fornecedor": "Beta Networks Portugal",
        "ref": "BN/2026/887",
        "linhas": [
            ("Switch 48p PoE+ (equivalente)", "4", "1.050,00", "4.200,00"),
            ("AP Wi-Fi 6 dual radio", "12", "228,00", "2.736,00"),
            ("Serviços de instalação", "1", "2.400,00", "2.400,00"),
        ],
        "total": "11.485,28",
        "iva": "Valor final, IVA incluído.",
        "pagamento": "Pagamento: 50% na adjudicação, 50% a 60 dias.",
        "entrega": "Entrega em 25 dias úteis.",
        "garantia": "Garantia de 24 meses.",
        "validade": "Validade da proposta: 45 dias.",
    },
    {
        "ficheiro": "proposta_gama.pdf",
        "fornecedor": "Gama Telecom SA",
        "ref": "GT-9921",
        "linhas": [
            ("Switch gerido 48 portas", "4", "1.320,00", "5.280,00"),
            ("Access point Wi-Fi 6E", "12", "290,00", "3.480,00"),
            ("Projecto, instalação e formação", "1", "2.100,00", "2.100,00"),
        ],
        "total": "10.860,00",
        "iva": "Aos valores apresentados acresce IVA.",
        "pagamento": "Pagamento a 90 dias.",
        "entrega": "Prazo de entrega: 10 dias úteis.",
        "garantia": "Garantia 60 meses com substituição avançada.",
        "validade": "Proposta válida por 60 dias.",
    },
    {
        "ficheiro": "proposta_delta.pdf",
        "fornecedor": "Delta IT Solutions",
        "ref": "DIT-2026-33",
        "linhas": [
            ("Switch 48 portas", "4", "980,00", "3.920,00"),
            ("Access point", "12", "199,00", "2.388,00"),
            ("Mão de obra", "1", "1.200,00", "1.200,00"),
        ],
        "total": "7.508,00",
        "iva": "",
        "pagamento": "",
        "entrega": "Entrega imediata de stock.",
        "garantia": "Garantia 12 meses.",
        "validade": "",
    },
    {
        "ficheiro": "proposta_epsilon.pdf",
        "fornecedor": "Epsilon Redes e Segurança",
        "ref": "EPS/26/0455",
        "linhas": [
            ("Switch PoE+ 48 portas empilhável", "4", "1.240,00", "4.960,00"),
            ("Access point Wi-Fi 6 exterior", "12", "265,00", "3.180,00"),
            ("Instalação, config. e documentação", "1", "1.600,00", "1.600,00"),
        ],
        "total": "9.740,00",
        "iva": "Preços sem IVA. Acresce IVA à taxa de 23%.",
        "pagamento": "Pagamento: 45 dias data factura.",
        "entrega": "Prazo de entrega: 20 dias úteis.",
        "garantia": "Garantia: 3 anos.",
        "validade": "Válida por 30 dias.",
    },
    {
        "ficheiro": "proposta_zeta.pdf",
        "fornecedor": "Zeta Infraestruturas",
        "ref": "Z-2026-0071",
        "linhas": [
            ("Switch 48 portas PoE+", "4", "1.150,00", "4.600,00"),
            ("Access point Wi-Fi 6", "12", "240,00", "2.880,00"),
            ("Instalação", "1", "1.400,00", "1.400,00"),
        ],
        "total": "8.880,00",
        "iva": "Acresce IVA.",
        "pagamento": "Pronto pagamento com 3% de desconto, ou 30 dias.",
        "entrega": "Prazo de entrega: 30 dias úteis.",
        "garantia": "Garantia 24 meses.",
        "validade": "Proposta válida 15 dias.",
    },
]


def proposta(destino: Path, dados: dict) -> None:
    """PT-PT: Uma proposta comercial. / EN-UK: One commercial quote."""
    c = canvas.Canvas(str(destino), pagesize=A4)

    c.setFont("Helvetica-Bold", 14)
    c.drawString(25 * mm, ALTURA - 25 * mm, dados["fornecedor"])
    c.setFont("Helvetica", 9)
    c.drawString(25 * mm, ALTURA - 31 * mm, "Proposta comercial — Renovação de rede")
    c.drawRightString(185 * mm, ALTURA - 25 * mm, f"Referência: {dados['ref']}")
    c.drawRightString(185 * mm, ALTURA - 31 * mm, "Data: 12/08/2026")

    y = ALTURA - 48 * mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(25 * mm, y, "Descrição")
    c.drawRightString(120 * mm, y, "Qtd.")
    c.drawRightString(150 * mm, y, "Preço unit.")
    c.drawRightString(185 * mm, y, "Total")
    c.setLineWidth(0.6)
    c.line(25 * mm, y - 2 * mm, 185 * mm, y - 2 * mm)

    y -= 8 * mm
    c.setFont("Helvetica", 9)
    for descricao, quantidade, unitario, total in dados["linhas"]:
        c.drawString(25 * mm, y, descricao)
        c.drawRightString(120 * mm, y, quantidade)
        c.drawRightString(150 * mm, y, f"{unitario} €")
        c.drawRightString(185 * mm, y, f"{total} €")
        y -= 6 * mm

    y -= 3 * mm
    c.line(120 * mm, y, 185 * mm, y)
    y -= 7 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(150 * mm, y, "TOTAL:")
    c.drawRightString(185 * mm, y, f"{dados['total']} €")

    y -= 8 * mm
    c.setFont("Helvetica", 9)
    if dados["iva"]:
        c.drawRightString(185 * mm, y, dados["iva"])
        y -= 10 * mm

    y -= 6 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(25 * mm, y, "Condições")
    y -= 7 * mm
    c.setFont("Helvetica", 9)
    for linha in ("pagamento", "entrega", "garantia", "validade"):
        if dados[linha]:
            c.drawString(25 * mm, y, dados[linha])
            y -= 6 * mm

    c.setFont("Helvetica-Oblique", 7)
    c.drawString(
        25 * mm, 15 * mm,
        "Documento de exemplo gerado para testes — fornecedor fictício. Created by Redfox using Claude.",
    )
    c.showPage()
    c.save()


def main(argv: list[str] | None = None) -> int:
    argumentos = argv if argv is not None else sys.argv[1:]
    pasta = Path(argumentos[0]) if argumentos else Path("exemplos")
    pasta.mkdir(parents=True, exist_ok=True)

    formulario(pasta / "formulario_acessos.pdf")
    print(f"Criado: {pasta / 'formulario_acessos.pdf'}")

    for dados in PROPOSTAS:
        caminho = pasta / dados["ficheiro"]
        proposta(caminho, dados)
        print(f"Criado: {caminho}")

    print(
        f"\n{len(PROPOSTAS) + 1} ficheiros em {pasta}.\n"
        "Experimente: o formulário no separador Formulários, as propostas no separador Comparar."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
