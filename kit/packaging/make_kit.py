# -*- coding: utf-8 -*-
"""Monta o kit de patch PT-BR a partir do build (uso interno; este script não vai para o zip).

kit/PTBR_Patch/localization           : só os arquivos traduzidos que são diferentes do original
kit/PTBR_Patch/hashes_originais.json  : SHA-256 do original de cada arquivo do kit
kit/packaging/Output/PTBR_Patch.zip   : o kit pronto para distribuir (sem backup_original)
"""

import hashlib
import json
import os
import shutil
import zipfile

PACOTE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(PACOTE)
PATCH = os.path.join(KIT, "PTBR_Patch")
LOC = os.path.join(PATCH, "localization")
RAIZ = os.path.dirname(KIT)
BUILD = os.path.join(RAIZ, "build")
ORIGINAL = os.path.join(RAIZ, "backup")
SAIDA = os.path.join(PACOTE, "Output")


def sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def arquivos_em(raiz):
    saida = []
    for pasta, _, nomes in os.walk(raiz):
        for nome in nomes:
            rel = os.path.relpath(os.path.join(pasta, nome), raiz)
            saida.append(rel.replace(os.sep, "/"))
    return sorted(saida)


def no_disco(raiz, rel):
    return os.path.join(raiz, *rel.split("/"))


def sincronizar():
    shutil.rmtree(LOC, ignore_errors=True)
    originais = {}
    copiados = 0
    for rel in arquivos_em(BUILD):
        traduzido = no_disco(BUILD, rel)
        original = no_disco(ORIGINAL, rel)
        if os.path.exists(original):
            hash_original = sha256(original)
            if hash_original == sha256(traduzido):
                continue  # igual ao original: não entra no kit
            originais[rel] = hash_original
        destino = no_disco(LOC, rel)
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        shutil.copy2(traduzido, destino)
        copiados += 1
    with open(os.path.join(PATCH, "hashes_originais.json"), "w", encoding="utf-8") as f:
        json.dump(originais, f, ensure_ascii=False, indent=2)
    return copiados


def gerar_zip():
    os.makedirs(SAIDA, exist_ok=True)
    destino = os.path.join(SAIDA, "PTBR_Patch.zip")
    if os.path.exists(destino):
        os.remove(destino)
    with zipfile.ZipFile(destino, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for rel in arquivos_em(PATCH):
            if rel.startswith("backup_original/"):
                continue
            z.write(no_disco(PATCH, rel), arcname="PTBR_Patch/" + rel)
    return destino


if __name__ == "__main__":
    n = sincronizar()
    zip_path = gerar_zip()
    print(n, "arquivos em localization")
    print("zip:", zip_path, os.path.getsize(zip_path), "bytes")
