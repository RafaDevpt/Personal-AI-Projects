# Created by Redfox using Claude
#
# PT-PT: Imagem de linha de comandos do VMware-Fleet-Console. A interface gráfica não
#        corre aqui: num contentor não há ecrã, e é a linha de comandos que
#        faz sentido automatizar. Os ficheiros de entrada e de saída, e a
#        configuração, vivem em /dados, que se monta a partir do anfitrião.
#        Nada de pessoal entra na imagem: credenciais e inventários são
#        passados na altura de correr.
#
# EN-UK: Command-line image for VMware-Fleet-Console. The graphical interface does not
#        run here: a container has no screen, and the command line is what
#        makes sense to automate. Input and output files, and configuration,
#        live in /dados, mounted from the host. Nothing personal goes into the
#        image: credentials and inventories are passed in at run time.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    HOME=/dados

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# PT-PT: utilizador sem privilégios; o código fica só de leitura para ele.
# EN-UK: unprivileged user; the code stays read-only to it.
RUN useradd --uid 10001 --home-dir /dados --no-create-home app \
 && mkdir -p /dados && chown app:app /dados
USER app
WORKDIR /dados

ENTRYPOINT ["python", "-m", "vfc"]
CMD ["--help"]
