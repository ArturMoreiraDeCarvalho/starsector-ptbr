# -*- coding: utf-8 -*-
"""Confere a tradução contra a tabela de termos do GLOSSARIO.txt.

Para cada termo "EN | PT" da tabela, procura textos cujo inglês contém o termo e cujo português
não contém nenhuma forma esperada. É uma lista para revisão, não uma correção automática:
há casos legítimos (plural, flexão, frase reescrita).

Uso:
    python -X utf8 tools/glossario.py            resumo por termo
    python -X utf8 tools/glossario.py "fleet"    lista os casos de um termo
"""
import glob
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITS = os.path.join(RAIZ, "units")
IGNORAR_CTX = ("DEV ", "$", "set ", "Player Luddic")


def termos():
    pares = []
    with open(os.path.join(RAIZ, "GLOSSARIO.txt"), encoding="utf-8") as f:
        for ln in f:
            cols = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(cols) != 2 or cols[0] in ("EN", "---") or set(cols[0]) <= set("-"):
                continue
            en = [x.strip() for x in cols[0].split("/")]
            pt = [x.strip() for x in cols[1].split("/")]
            for i, e in enumerate(en):
                alvo = pt[i] if i < len(pt) else pt[-1]
                formas = [re.sub(r"\(.*?\)", "", a).strip() for a in re.split(r"[;,]", alvo)]
                formas += re.findall(r"\(([^)]*)\)", alvo)
                formas = [x for x in formas if x]
                if e and formas:
                    pares.append((e, formas))
    return pares


def radical(p):
    """Forma tolerante a plural e gênero: 'fragata' casa com 'fragatas'."""
    p = p.lower()
    return re.sub(r"(ção|ções|ão|ões|ães|ais|al|eis|el|is|il|a|o|e|s)$", "", p) if len(p) > 4 else p


def textos():
    for pt_path in sorted(glob.glob(os.path.join(UNITS, "*.pt.json"))):
        with open(pt_path, encoding="utf-8") as f:
            pt = json.load(f)
        with open(pt_path.replace(".pt.json", ".en.json"), encoding="utf-8") as f:
            en = {str(it["i"]): it["en"] for it in json.load(f)["items"]}
        bloco = os.path.basename(pt_path)[:-8]
        for k, v in pt.items():
            yield bloco, k, en.get(k, ""), v


def main():
    filtro = sys.argv[1].lower() if len(sys.argv) > 1 else None
    pares = termos()
    dados = list(textos())
    total = 0
    for e, formas in pares:
        if filtro and e.lower() != filtro:
            continue
        padrao = re.compile(r"\b" + re.escape(e) + r"s?\b", re.I)
        radicais = [radical(f) for f in formas]
        casos = []
        for bloco, k, en, pt in dados:
            if en.startswith(IGNORAR_CTX) or not padrao.search(re.sub(r"\$\w+", "", en)):
                continue
            baixo = pt.lower()
            if any(r in baixo for r in radicais):
                continue
            casos.append((bloco, k, en, pt))
        total += len(casos)
        if filtro:
            for bloco, k, en, pt in casos:
                print(f"{bloco} #{k}\n  EN: {en[:160]}\n  PT: {pt[:160]}")
        elif casos:
            print(f"{e:28} -> {' / '.join(formas):40} {len(casos):5} para revisar")
    print(f"total: {total} casos para revisar ({len(pares)} termos)")


if __name__ == "__main__":
    main()
