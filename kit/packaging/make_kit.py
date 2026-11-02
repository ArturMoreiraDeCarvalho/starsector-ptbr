# -*- coding: utf-8 -*-
"""Monta o kit de patch PT-BR a partir do build (uso interno; este script não vai para o zip).

kit/PTBR_Patch/localization           : só os arquivos traduzidos que são diferentes do original
kit/PTBR_Patch/hashes_originais.json  : SHA-256 do original de cada arquivo do kit
kit/packaging/Output/PTBR_Patch.zip   : o kit pronto para distribuir (sem backup_original)
kit/PTBR_Patch/mescla.dat             : linha original -> linha traduzida, para traduzir arquivos que outro mod alterou

Formato do mescla.dat (binário, linhas separadas por \\n):
    PTBR-MESCLA 1
    @<caminho>\\t<n>             seguido de n pares de linhas:
    <sha256 da linha original sem \\r, 16 primeiros hex>
    <linha traduzida, bytes UTF-8, sem \\r>
Só entram linhas cuja tradução é a mesma em todo o arquivo e que não aparecem sem tradução em outro ponto.
"""

import difflib
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


TEXTO = (".csv", ".json", ".faction", ".variant", ".skin", ".skill", ".txt", ".java")


def chave_linha(linha):
    return hashlib.sha256(linha).hexdigest()[:16]


def sem_cr(linha):
    return linha[:-1] if linha.endswith(b"\r") else linha


def mapa_linhas(original, traduzido):
    """Pares (chave da linha original, linha traduzida) das linhas que a tradução trocou."""
    with open(original, "rb") as f:
        a = [sem_cr(x) for x in f.read().split(b"\n")]
    with open(traduzido, "rb") as f:
        b = [sem_cr(x) for x in f.read().split(b"\n")]
    ka = [chave_linha(x) for x in a]
    kb = [chave_linha(x) for x in b]
    mapa, ambiguas, iguais = {}, set(), set()
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ka, kb, autojunk=False).get_opcodes():
        if tag == "equal":
            iguais.update(ka[i1:i2])
            continue
        if tag != "replace" or i2 - i1 != j2 - j1:
            continue  # blocos com número diferente de linhas ficam de fora
        for k in range(i2 - i1):
            if not a[i1 + k].strip():
                continue
            chave, alvo = ka[i1 + k], b[j1 + k]
            if chave in mapa and mapa[chave] != alvo:
                ambiguas.add(chave)
            mapa.setdefault(chave, alvo)
    for chave in ambiguas | (iguais & set(mapa)):
        mapa.pop(chave, None)
    return mapa


def gerar_mescla():
    partes = [b"PTBR-MESCLA 1"]
    arquivos = linhas = 0
    for rel in arquivos_em(LOC):
        if rel.startswith("graphics/") or not rel.endswith(TEXTO):
            continue
        original = no_disco(ORIGINAL, rel)
        if not os.path.exists(original):
            continue
        mapa = mapa_linhas(original, no_disco(LOC, rel))
        if not mapa:
            continue
        partes.append(b"@" + rel.encode("utf-8") + b"\t" + str(len(mapa)).encode("ascii"))
        for chave in sorted(mapa):
            partes.append(chave.encode("ascii"))
            partes.append(mapa[chave])
        arquivos += 1
        linhas += len(mapa)
    with open(os.path.join(PATCH, "mescla.dat"), "wb") as f:
        f.write(b"\n".join(partes) + b"\n")
    return arquivos, linhas


def gerar_zip():
    os.makedirs(SAIDA, exist_ok=True)
    destino = os.path.join(SAIDA, "PTBR_Patch.zip")
    if os.path.exists(destino):
        os.remove(destino)
    with zipfile.ZipFile(destino, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for rel in arquivos_em(PATCH):
            if rel.startswith("backup_original/") or "__pycache__/" in rel:
                continue
            z.write(no_disco(PATCH, rel), arcname="PTBR_Patch/" + rel)
    return destino


if __name__ == "__main__":
    n = sincronizar()
    m_arq, m_lin = gerar_mescla()
    zip_path = gerar_zip()
    print(n, "arquivos em localization")
    print("mescla:", m_arq, "arquivos,", m_lin, "linhas")
    print("zip:", zip_path, os.path.getsize(zip_path), "bytes")
