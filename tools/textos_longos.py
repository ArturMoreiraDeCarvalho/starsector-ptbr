# -*- coding: utf-8 -*-
"""Lista rótulos curtos cuja tradução ficou bem maior que o inglês e pode ser cortada na tela.

Olha só textos curtos de uma linha (botões, colunas, títulos de tooltip), que são os que ficam em
espaço fixo. Textos longos quebram linha sozinhos e não entram.

Uso:
    python -X utf8 tools/textos_longos.py               grava relatorios/textos_longos.txt
    python -X utf8 tools/textos_longos.py --max-en 20   só rótulos com até 20 letras em inglês
"""
import argparse
import glob
import json
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITS = os.path.join(RAIZ, "units")
SAIDA = os.path.join(RAIZ, "relatorios", "textos_longos.txt")
CATEGORIAS = ("jar", "ui", "data", "java")   # rules, desc e txt são texto corrido


def visivel(s):
    """Tamanho que aparece na tela: tira %s, $variaveis e marcações {{...}}."""
    s = re.sub(r"\{\{[^}]*\}\}", "XXXX", s)
    s = re.sub(r"%[-+ 0#]*\d*(?:\.\d+)?[sdfx%]", "00", s)
    s = re.sub(r"\$[A-Za-z_][\w.]*", "XXXXXX", s)
    return len(s.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-en", type=int, default=30, help="tamanho máximo do inglês (padrão 30)")
    ap.add_argument("--razao", type=float, default=1.35, help="PT/EN mínimo para listar (padrão 1.35)")
    ap.add_argument("--folga", type=int, default=4, help="diferença mínima em letras (padrão 4)")
    a = ap.parse_args()

    achados = []
    for en_path in sorted(glob.glob(os.path.join(UNITS, "*.en.json"))):
        pt_path = en_path[:-len(".en.json")] + ".pt.json"
        if not os.path.exists(pt_path):
            continue
        with open(en_path, encoding="utf-8") as f:
            bloco = json.load(f)
        if bloco.get("cat") not in CATEGORIAS:
            continue
        with open(pt_path, encoding="utf-8") as f:
            pt = json.load(f)
        for it in bloco["items"]:
            en = it["en"]
            tr = pt.get(str(it["i"]))
            if not tr or "\n" in en or "\n" in tr:
                continue
            le, lp = visivel(en), visivel(tr)
            if le == 0 or le > a.max_en:
                continue
            if lp >= le * a.razao and lp - le >= a.folga:
                achados.append((lp - le, lp / le, bloco["chunk"], it["i"], en, tr, it.get("ctx", "")))

    achados.sort(key=lambda x: (-x[0], -x[1]))
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write("Rótulos curtos que ficaram bem maiores em português (podem cortar na tela).\n")
        f.write(f"Critério: inglês com até {a.max_en} letras, português {a.razao:.2f}x maior e "
                f"pelo menos {a.folga} letras a mais. Total: {len(achados)}.\n")
        f.write("Confira no jogo. Para encurtar, edite units/NNNN_<tipo>.pt.json no item indicado e rode\n")
        f.write("python -X utf8 tools/sstr.py validate e build.\n\n")
        for dif, razao, chunk, i, en, tr, ctx in achados:
            f.write(f"[{chunk:04d} #{i}] +{dif} letras ({razao:.1f}x)  {ctx}\n")
            f.write(f"    EN: {en}\n    PT: {tr}\n\n")
    print(f"{len(achados)} rótulos listados em {os.path.relpath(SAIDA, RAIZ)}")


if __name__ == "__main__":
    main()
