# -*- coding: utf-8 -*-
"""Testes do kit PT-BR (instalador .bat/.ps1 e script Python) em cópias temporárias.

Usa build/ (traduzido) e backup/ (originais). Não toca no jogo instalado.
Uso:  python -X utf8 kit/packaging/teste_kit.py
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

PACOTE = os.path.dirname(os.path.abspath(__file__))
RAIZ_PROJ = os.path.dirname(os.path.dirname(PACOTE))
KIT_SRC = os.path.join(RAIZ_PROJ, "kit", "PTBR_Patch")
ORIG_SRC = os.path.join(RAIZ_PROJ, "backup")
TRAD_SRC = os.path.join(RAIZ_PROJ, "build")
ZIP = os.path.join(PACOTE, "Output", "PTBR_Patch.zip")
RAIZ = os.path.join(tempfile.gettempdir(), "ptbr_teste_kit")
FALHAS = []


def check(c, m):
    print(("OK    " if c else "FALHA ") + m)
    if not c:
        FALHAS.append(m)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def listar(r):
    out = {}
    for d, _, ns in os.walk(r):
        for n in ns:
            p = os.path.join(d, n)
            out[os.path.relpath(p, r).replace(os.sep, "/")] = p
    return out


def nd(r, rel):
    return os.path.join(r, *rel.split("/"))


LOC = listar(os.path.join(KIT_SRC, "localization"))
HL = {r: sha(p) for r, p in LOC.items()}
HO = {r: sha(nd(ORIG_SRC, r)) for r in LOC}


def jogo_original(dest):
    """Monta um starsector-core com os originais: só os arquivos que o kit troca, mais o jar."""
    for r in LOC:
        os.makedirs(os.path.dirname(nd(dest, r)), exist_ok=True)
        shutil.copy2(nd(ORIG_SRC, r), nd(dest, r))


def jogo_traduzido(dest):
    for r, p in LOC.items():
        os.makedirs(os.path.dirname(nd(dest, r)), exist_ok=True)
        shutil.copy2(p, nd(dest, r))


def ambiente(nome, montar, base=None):
    d = os.path.join(base or RAIZ, nome)
    if os.path.exists(d):
        shutil.rmtree(d, onerror=lambda f, p, e: (os.chmod(p, 0o666), f(p)))
    os.makedirs(d)
    shutil.copytree(KIT_SRC, os.path.join(d, "PTBR_Patch"), ignore=shutil.ignore_patterns("backup_original"))
    montar(os.path.join(d, "starsector-core"))
    return d


def ps(d, acao, *extra):
    s = os.path.join(d, "PTBR_Patch", "_instalador.ps1")
    r = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", s, "-Acao", acao,
                        "-SemPausa", "-SemElevar", *extra],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=RAIZ)
    return r.returncode, r.stdout + r.stderr


def py(d, acao, *extra):
    s = os.path.join(d, "PTBR_Patch", "_swapLangFile.py")
    r = subprocess.run([sys.executable, "-X", "utf8", s, acao, *extra], capture_output=True, text=True,
                       encoding="utf-8", cwd=RAIZ)
    return r.returncode, r.stdout + r.stderr


def bat(d, nome):
    r = subprocess.run(["cmd.exe", "/c", os.path.join(d, "PTBR_Patch", nome)], input="\n", capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=RAIZ)
    return r.returncode, r.stdout + r.stderr


def estado(d, alvo, passo):
    j = os.path.join(d, "starsector-core")
    ruins = [r for r in LOC if not os.path.isfile(nd(j, r)) or sha(nd(j, r)) != alvo[r]]
    check(not ruins, f"{passo}: {len(LOC) - len(ruins)}/{len(LOC)} arquivos corretos {ruins[:3]}")


def bkp(d):
    return {r for r in listar(os.path.join(d, "PTBR_Patch", "backup_original")) if r != "_manifesto.json"}


def manif(d):
    p = os.path.join(d, "PTBR_Patch", "backup_original", "_manifesto.json")
    if not os.path.isfile(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def icacls(caminho, *args):
    subprocess.run(["icacls", caminho, *args], capture_output=True)


# ------------------------------------------------------------------ testes
def t_kit():
    print("\n== 0. conteúdo do kit")
    with open(os.path.join(KIT_SRC, "hashes_originais.json"), encoding="utf-8") as f:
        h = json.load(f)
    check(set(h) == set(LOC), f"hashes_originais.json com {len(h)} entradas = arquivos do kit")
    check(all(sha(nd(ORIG_SRC, r)) == h[r] for r in h), "hashes batem com os originais")
    check(all(HL[r] != h[r] for r in h), "nenhum arquivo do kit igual ao original")
    check(all(sha(nd(TRAD_SRC, r)) == HL[r] for r in LOC), "kit igual ao build")
    fontes = [r for r in LOC if r.startswith("graphics/fonts/")]
    check(len(fontes) > 0, f"{len(fontes)} arquivos de fonte no kit")


def t_original():
    print("\n== 1. jogo original: instalar, repetir, desinstalar")
    d = ambiente("orig", jogo_original)
    rc, out = ps(d, "pt"); check(rc == 0, f"pt (ps) retorna 0 ({rc}) {out[-300:] if rc else ''}")
    estado(d, HL, "apos pt"); check(len(bkp(d)) == len(LOC), f"backup com {len(bkp(d))} originais")
    check(manif(d) == {"novos": []}, "manifesto legível pelo Python")
    rc, _ = ps(d, "pt"); check(rc == 0, "pt repetido"); estado(d, HL, "pt repetido")
    rc, _ = ps(d, "en"); check(rc == 0, "en (ps)"); estado(d, HO, "apos en")
    check(manif(d) is None, "manifesto removido")
    rc, _ = ps(d, "pt", "-Jogo", d); check(rc == 0, "-Jogo com a pasta raiz"); estado(d, HL, "-Jogo raiz")
    rc, _ = ps(d, "en", "-Jogo", os.path.join(d, "starsector-core")); check(rc == 0, "-Jogo com starsector-core")
    estado(d, HO, "-Jogo core")


def t_python():
    print("\n== 2. script Python e convivência com o instalador")
    d = ambiente("py", jogo_original)
    rc, _ = py(d, "pt"); check(rc == 0, "pt (py)"); estado(d, HL, "py pt")
    rc, _ = ps(d, "en"); check(rc == 0, "en (ps) depois de pt (py)"); estado(d, HO, "ps en")
    rc, _ = ps(d, "pt"); rc2, _ = py(d, "en"); check(rc == rc2 == 0, "pt (ps) e en (py)"); estado(d, HO, "py en")
    alvo = sorted(LOC)[5]
    os.remove(nd(os.path.join(d, "starsector-core"), alvo))
    rc, _ = ps(d, "pt"); check(rc == 0 and manif(d) == {"novos": [alvo]}, "arquivo ausente vira 'novo' no manifesto")
    rc, out = py(d, "en"); check(rc == 0 and "1 arquivo(s) novo(s) removido(s)" in out, "Python remove o arquivo novo")


def t_traduzido():
    print("\n== 3. jogo já traduzido")
    d = ambiente("trad", jogo_traduzido)
    rc, _ = ps(d, "pt"); check(rc == 0 and not bkp(d), "pt sem criar backup")
    rc, out = ps(d, "en"); check(rc == 0 and "tinham original guardado" in out, "en avisa os arquivos sem original")


def t_recusa():
    print("\n== 4. arquivo de outro mod")
    d = ambiente("recusa", jogo_original)
    alvo = sorted(r for r in LOC if r.endswith(".csv"))[0]
    p = nd(os.path.join(d, "starsector-core"), alvo)
    with open(p, "wb") as f:
        f.write(b"outro mod")
    rc, out = ps(d, "pt"); check(rc == 1 and alvo in out, "recusa e cita o arquivo")
    with open(p, "rb") as f:
        check(f.read() == b"outro mod" and alvo not in bkp(d), "arquivo intacto e fora do backup")
    shutil.copy2(nd(ORIG_SRC, alvo), p)
    rc, _ = ps(d, "pt"); check(rc == 0, "recupera depois de restaurar"); estado(d, HL, "recuperado")


def t_versao():
    print("\n== 5. outra versão do jogo")
    d = ambiente("versao", jogo_original)
    jar = os.path.join(d, "starsector-core", "starfarer_obf.jar")
    with open(jar, "ab") as f:
        f.write(b"versao diferente")
    antes = sha(jar)
    rc, out = ps(d, "pt"); check(rc == 1 and "0.98a-RC8" in out, "instalador recusa outra versão")
    rc, out = py(d, "pt"); check(rc == 1 and "0.98a-RC8" in out, "Python recusa outra versão")
    check(sha(jar) == antes and not bkp(d), "nada foi alterado")


def t_permissao():
    print("\n== 6. pasta do kit protegida (erro 'acesso ao caminho data negado')")
    d = ambiente("perm", jogo_original)
    kit = os.path.join(d, "PTBR_Patch")
    icacls(kit, "/deny", f"{os.environ['USERNAME']}:(AD,WD)")
    try:
        rc, out = ps(d, "pt")
        check(rc == 3 and "administrador" in out, f"pede administrador em vez de falhar no meio ({rc})")
        estado(d, HO, "jogo intacto")
    finally:
        icacls(kit, "/remove:d", os.environ["USERNAME"])
    rc, _ = ps(d, "pt"); check(rc == 0, "com permissão, instala"); estado(d, HL, "apos permissão")


def t_caminho():
    print("\n== 7. caminho com espaços, acentos e colchetes")
    base = os.path.join(RAIZ, "Jogos [teste] Ação e Espaço")
    os.makedirs(base, exist_ok=True)
    d = ambiente("Starsector", jogo_original, base=base)
    rc, _ = ps(d, "pt"); check(rc == 0, "pt"); estado(d, HL, "apos pt")
    rc, _ = ps(d, "en"); check(rc == 0, "en"); estado(d, HO, "apos en")


def t_zip():
    print("\n== 8. zip de distribuição e .bat")
    with zipfile.ZipFile(ZIP) as z:
        nomes = set(z.namelist())
        pref = "PTBR_Patch/localization/"
        loc_zip = {n[len(pref):] for n in nomes if n.startswith(pref) and not n.endswith("/")}
        check(loc_zip == set(LOC), f"zip com {len(loc_zip)} arquivos em localization")
        check(not any("backup_original" in n for n in nomes), "zip sem backup_original")
        for n in ("INSTALAR.bat", "DESINSTALAR.bat", "_instalador.ps1", "_swapLangFile.py", "README.txt"):
            check("PTBR_Patch/" + n in nomes, f"zip contém {n}")
        d = os.path.join(RAIZ, "zip")
        os.makedirs(d)
        z.extractall(d)
    jogo_original(os.path.join(d, "starsector-core"))
    rc, out = bat(d, "INSTALAR.bat"); check(rc == 0 and "Pronto" in out, f"INSTALAR.bat ({rc})")
    estado(d, HL, "apos INSTALAR"); check("Tradução PT-BR" in out, "acentos corretos no console")
    rc, out = bat(d, "DESINSTALAR.bat"); check(rc == 0 and "Pronto" in out, f"DESINSTALAR.bat ({rc})")
    estado(d, HO, "apos DESINSTALAR")


if __name__ == "__main__":
    if os.path.exists(RAIZ):
        shutil.rmtree(RAIZ)
    os.makedirs(RAIZ)
    try:
        for t in (t_kit, t_original, t_python, t_traduzido, t_recusa, t_versao, t_permissao, t_caminho, t_zip):
            t()
    finally:
        shutil.rmtree(RAIZ, ignore_errors=True)
    print(f"\nFalhas: {len(FALHAS)}")
    for f in FALHAS:
        print("  -", f)
    sys.exit(1 if FALHAS else 0)
