# -*- coding: utf-8 -*-
"""Revisão ortográfica e gramatical automática das traduções (LanguageTool, pt-BR, roda localmente).

Não corrige nada: grava relatorios/ortografia.txt com o que merece olhar. Filtra o ruído mais comum:
nomes que ficam em inglês de propósito (palavras que já aparecem no texto original), variáveis ($x, %s, {{...}}),
e regras de estilo que não valem para texto de jogo.

Preparação (uma vez), com um ambiente isolado:
    python -m venv ref/venv_lt
    ref/venv_lt/Scripts/python.exe -m pip install language-tool-python
Uso:
    ref/venv_lt/Scripts/python.exe -X utf8 tools/revisar_ortografia.py [--amostra N] [--categorias jar,ui,...]
Na primeira execução o LanguageTool baixa o servidor (cerca de 200 MB) para a pasta de cache do usuário.
"""
import argparse
import collections
import glob
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITS = os.path.join(RAIZ, "units")
SAIDA = os.path.join(RAIZ, "relatorios", "ortografia.txt")

# regras que não ajudam em texto de jogo (maiúscula inicial, espaços, aspas, etc.)
IGNORAR_REGRAS = {
    "UPPERCASE_SENTENCE_START", "WHITESPACE_RULE", "COMMA_PARENTHESIS_WHITESPACE", "PORTUGUESE_WORD_REPEAT_BEGINNING_RULE",
    "DOUBLE_PUNCTUATION", "UNPAIRED_BRACKETS", "EN_QUOTES", "PT_QUOTES", "SENTENCE_WHITESPACE", "PUNTUACAO_FINAL",
    "PT_BARBARISMS_REPLACE", "PT_WORDINESS_REPLACE", "PT_REDUNDANCY_REPLACE", "PT_CLICHE_REPLACE",
    "PT_COMPOUNDS_POST_REFORM", "PORTUGUESE_WORD_COHERENCY", "READABILITY_RULE_SIMPLE", "READABILITY_RULE_DIFFICULT",
    "UPPERCASE_SENTENCE_START_PT", "SPACE_BEFORE_PARENTHESIS", "TYPOGRAPHY", "UPPERCASE_AFTER_COMMA",
    "DEPOIS_DE_APÓS", "O_QUANTO_ANTES_BR", "FORMAL_PRA_PARA", "CORRER_RISCO_ARRISCAR", "COLOCAÇÃO_ADVÉRBIO",
}
# regras de estilo (sugestões de reescrita, não erros): ignoradas por prefixo
IGNORAR_PREFIXOS = ("PT_WORDINESS", "PT_CLICHE", "PT_REDUNDANCY", "PT_BARBARISMS", "PT_COMPOUNDS", "READABILITY",
                    "STYLE", "FORMAL_", "INFORMAL_", "PT_REPLACE_", "AGREEMENT_SUGGESTION_")
# categorias de texto (rules e desc são texto corrido e grandes; entram com --categorias)
PADRAO = ("jar", "ui", "data", "txt", "java")


def limpar(s):
    """Troca variáveis e marcações por palavras neutras para o revisor não reclamar delas."""
    s = re.sub(r"\{\{([^}]*)\}\}", r"\1", s)
    s = re.sub(r"%[-+ 0#]*\d*(?:\.\d+)?[sdfx]", "10", s)
    s = re.sub(r"%%", "%", s)
    s = re.sub(r"\$[A-Za-z_][\w.]*", "Nome", s)
    s = re.sub(r"\[[^\]]*\]", "", s)           # [tags] do jogo
    s = s.replace("\\n", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", s).strip()


def carregar(categorias):
    itens = []
    for en_path in sorted(glob.glob(os.path.join(UNITS, "*.en.json"))):
        pt_path = en_path[:-len(".en.json")] + ".pt.json"
        if not os.path.exists(pt_path):
            continue
        with open(en_path, encoding="utf-8") as f:
            bloco = json.load(f)
        if bloco.get("cat") not in categorias:
            continue
        with open(pt_path, encoding="utf-8") as f:
            pt = json.load(f)
        for it in bloco["items"]:
            tr = pt.get(str(it["i"]))
            if tr and re.search(r"[A-Za-zÀ-ÿ]{3,}", tr):
                itens.append((bloco["chunk"], it["i"], it["en"], tr, it.get("ctx", "")))
    return itens


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--amostra", type=int, default=0, help="só os N primeiros textos (teste)")
    ap.add_argument("--categorias", default=",".join(PADRAO))
    ap.add_argument("--tamanho-lote", type=int, default=40000, help="caracteres por chamada")
    ap.add_argument("--saida", default=SAIDA, help="arquivo do relatório (padrão relatorios/ortografia.txt)")
    a = ap.parse_args()
    saida = a.saida

    try:
        import language_tool_python
    except ImportError:
        print("Instale language-tool-python (veja o topo deste arquivo).")
        return 1

    itens = carregar(tuple(a.categorias.split(",")))
    if a.amostra:
        itens = itens[:a.amostra]
    print(f"{len(itens)} textos para revisar")

    tool = language_tool_python.LanguageTool("pt-BR")
    achados = []
    ruido_nomes = 0
    lote, tam, inicio = [], 0, 0

    def processar(lote):
        nonlocal ruido_nomes
        texto, faixas = "", []
        for idx, (_, _, en, tr, _) in enumerate(lote):
            c = limpar(tr)
            faixas.append((len(texto), len(texto) + len(c), idx))
            texto += c + "\n\n"
        for m in tool.check(texto):
            if m.rule_id in IGNORAR_REGRAS or m.rule_id.startswith(IGNORAR_PREFIXOS):
                continue
            for ini, fim, idx in faixas:
                if ini <= m.offset <= fim:
                    break
            else:
                continue
            chunk, i, en, tr, ctx = lote[idx]
            palavra = texto[m.offset:m.offset + m.error_length]
            if re.search(r"\bNome\b", palavra) or "$" in en and re.search(r"\bNome\b", texto[max(0, m.offset - 12):m.offset + m.error_length + 12]):
                ruido_nomes += 1   # envolve uma variável do jogo ($x), que não dá para revisar
                continue
            if m.rule_id.startswith("MORFOLOGIK") or "SPELL" in m.rule_id.upper():
                if any(w.lower() in en.lower() for w in re.findall(r"[A-Za-zÀ-ÿ'\-]{2,}", palavra)):
                    ruido_nomes += 1   # nome que ficou em inglês de propósito
                    continue
                if re.search(r"\d|^[A-Z]{2,}$", palavra):
                    continue
            achados.append((m.rule_id, chunk, i, palavra, m.message, list(m.replacements[:3]), en, tr))

    for item in itens:
        lote.append(item)
        tam += len(item[3]) + 2
        if tam >= a.tamanho_lote:
            processar(lote)
            inicio += len(lote)
            print(f"  {inicio}/{len(itens)}", flush=True)
            lote, tam = [], 0
    if lote:
        processar(lote)
    tool.close()

    por_regra = collections.Counter(r for r, *_ in achados)
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    with open(saida, "w", encoding="utf-8") as f:
        f.write(f"Revisão automática (LanguageTool pt-BR): {len(achados)} pontos em {len(itens)} textos.\n")
        f.write(f"Ignorados {ruido_nomes} avisos de palavras que já estão no texto original em inglês (nomes mantidos).\n")
        f.write("Resumo por regra:\n")
        for regra, n in por_regra.most_common():
            f.write(f"  {n:5d}  {regra}\n")
        f.write("\n")
        for regra, chunk, i, palavra, msg, sug, en, tr in sorted(achados, key=lambda x: (x[0], x[1], x[2])):
            f.write(f"[{chunk:04d} #{i}] {regra}: '{palavra}' -> {sug}\n    {msg}\n    EN: {en[:200]}\n    PT: {tr[:200]}\n\n")
    print(f"{len(achados)} pontos em {os.path.relpath(saida, RAIZ)}")
    for regra, n in por_regra.most_common(15):
        print(f"  {n:5d}  {regra}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
