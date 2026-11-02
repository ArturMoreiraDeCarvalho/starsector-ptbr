# -*- coding: utf-8 -*-
"""Coleta os SHA-256 de todas as versões já publicadas dos arquivos traduzidos do kit.

Lê o histórico do git do repositório público (cada commit que mexeu em kit/PTBR_Patch/localization) e grava
kit/packaging/anteriores.json:  { "caminho/relativo": ["sha256", ...] }

O make_kit.py usa esse arquivo para gerar PTBR_Patch/hashes_anteriores.json. Com ele, o instalador reconhece uma
tradução de versão antiga mesmo quando a pasta backup_original dela não existe mais.

Uso (rode antes de gerar uma versão nova, para incluir a versão que está publicada):
    python -X utf8 kit/packaging/coletar_anteriores.py [pasta-do-repositorio]
"""
import hashlib
import json
import os
import subprocess
import sys

PACOTE = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(PACOTE, "anteriores.json")
REPO_PADRAO = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(PACOTE))), "starsector-ptbr-github")
PREFIXO = "kit/PTBR_Patch/localization/"


def git(repo, *args, entrada=None):
    r = subprocess.run(["git", "-C", repo, *args], input=entrada, capture_output=True, check=True)
    return r.stdout


def main():
    repo = sys.argv[1] if len(sys.argv) > 1 else REPO_PADRAO
    if not os.path.isdir(os.path.join(repo, ".git")):
        print("Repositório não encontrado:", repo)
        return 1

    commits = git(repo, "log", "--format=%H", "--", PREFIXO.rstrip("/")).decode().split()
    pares = set()  # (blob, caminho)
    for c in commits:
        saida = git(repo, "ls-tree", "-r", "-z", c, "--", PREFIXO.rstrip("/")).decode("utf-8", "replace")
        for item in saida.split("\0"):
            if not item:
                continue
            meta, caminho = item.split("\t", 1)
            blob = meta.split()[2]
            pares.add((blob, caminho[len(PREFIXO):]))

    blobs = sorted({b for b, _ in pares})
    bruto = git(repo, "cat-file", "--batch", entrada=("\n".join(blobs) + "\n").encode())
    sha_do_blob, pos = {}, 0
    for blob in blobs:
        fim = bruto.index(b"\n", pos)
        _, _, tam = bruto[pos:fim].split()
        tam = int(tam)
        conteudo = bruto[fim + 1:fim + 1 + tam]
        sha_do_blob[blob] = hashlib.sha256(conteudo).hexdigest()
        pos = fim + 1 + tam + 1

    por_arquivo = {}
    for blob, caminho in pares:
        por_arquivo.setdefault(caminho, set()).add(sha_do_blob[blob])
    dados = {k: sorted(v) for k, v in sorted(por_arquivo.items())}
    with open(SAIDA, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=0)
    variantes = sum(len(v) for v in dados.values())
    print(f"{len(commits)} commits, {len(dados)} arquivos, {variantes} versões em {os.path.relpath(SAIDA)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
