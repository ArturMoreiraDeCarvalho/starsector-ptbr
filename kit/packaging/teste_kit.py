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


def carregar_swap():
    import importlib.util
    sys.dont_write_bytecode = True  # não deixa __pycache__ dentro do kit
    spec = importlib.util.spec_from_file_location("swap", os.path.join(KIT_SRC, "_swapLangFile.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def t_mescla():
    print("\n== 4b. arquivo alterado por outro mod: tradução parcial")
    swap = carregar_swap()
    # a mescla aplicada ao original precisa reproduzir a tradução (exceto blocos que mudaram de tamanho)
    tmp = os.path.join(RAIZ, "mescla_orig.tmp")
    exatos = total = 0
    for rel in sorted(swap.carregar_mescla()):
        total += 1
        n = swap.mesclar(nd(ORIG_SRC, rel), tmp, rel)
        with open(tmp, "rb") as f:
            obtido = f.read()
        with open(LOC[rel], "rb") as f:
            esperado = f.read()
        exatos += n > 0 and obtido.rstrip(b"\r\n") == esperado.rstrip(b"\r\n")
    os.remove(tmp)
    check(total > 600 and exatos >= total - 25, f"mescla do original reproduz a tradução em {exatos}/{total} arquivos")

    alvo = "data/strings/tips.json"
    d = ambiente("mescla", jogo_original)
    p = nd(os.path.join(d, "starsector-core"), alvo)
    with open(nd(ORIG_SRC, alvo), "rb") as f:
        linhas = f.read().split(b"\n")
    k = next(i for i, l in enumerate(linhas) if b"ordnance" in l.lower())
    linhas[k] = b'\t"Linha alterada por outro mod: keep me",\r' if linhas[k].endswith(b"\r") else b'\t"Linha alterada por outro mod: keep me",'
    linhas.insert(3, b'\t"Dica nova de outro mod",')
    modificado = b"\n".join(linhas)
    with open(p, "wb") as f:
        f.write(modificado)
    rc, out = ps(d, "pt")
    check(rc == 0 and "traduzidos em parte" in out and alvo in out, f"pt traduz em parte ({rc})")
    with open(p, "rb") as f:
        mesclado = f.read()
    check(b"keep me" in mesclado and b"Dica nova de outro mod" in mesclado, "linhas do outro mod mantidas")
    linhas_mod = set(modificado.split(b"\n"))
    traduzidas = sum(1 for l in mesclado.split(b"\n") if l not in linhas_mod)
    check(traduzidas > 20, f"{traduzidas} linhas traduzidas")
    with open(nd(os.path.join(d, "PTBR_Patch", "backup_original"), alvo), "rb") as f:
        check(f.read() == modificado, "backup guarda a versão do outro mod")
    check(alvo in (manif(d) or {}).get("mesclados", []), "manifesto registra o arquivo mesclado")
    e = os.path.join(RAIZ, "mescla_py.tmp")
    swap.mesclar(nd(os.path.join(d, "PTBR_Patch", "backup_original"), alvo), e, alvo)
    with open(e, "rb") as f:
        check(f.read() == mesclado, "PowerShell e Python geram o mesmo arquivo")
    os.remove(e)
    rc, _ = ps(d, "pt")
    with open(p, "rb") as f:
        check(rc == 0 and f.read() == mesclado, "pt repetido refaz a mescla sem perder o outro mod")
    rc, out = ps(d, "en")
    with open(p, "rb") as f:
        check(rc == 0 and f.read() == modificado, "en devolve a versão do outro mod")
    check(alvo not in bkp(d) and "tinham original" not in out, "en limpa o backup do arquivo mesclado")
    estado_outros = [r for r in LOC if r != alvo and sha(nd(os.path.join(d, "starsector-core"), r)) != HO[r]]
    check(not estado_outros, f"en: outros arquivos voltam ao original {estado_outros[:3]}")
    rc, _ = py(d, "pt")
    with open(p, "rb") as f:
        check(rc == 0 and f.read() == mesclado, "Python pt também traduz em parte")
    rc, _ = py(d, "en")
    with open(p, "rb") as f:
        check(rc == 0 and f.read() == modificado, "Python en devolve a versão do outro mod")


def registrar_anteriores(d, extras):
    """Soma hashes de 'versões antigas' ao hashes_anteriores.json da cópia do kit usada no teste."""
    p = os.path.join(d, "PTBR_Patch", "hashes_anteriores.json")
    dados = {}
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            dados = json.load(f)
    for r, hs in extras.items():
        dados[r] = sorted(set(dados.get(r, [])) | set(hs))
    with open(p, "w", encoding="utf-8") as f:
        json.dump(dados, f)


def t_atualizacao():
    print("\n== 4c. atualização de uma versão anterior do kit (arquivos sintéticos)")
    escolhidos = ([r for r in sorted(LOC) if r.endswith(".csv")][:2] + ["starfarer_obf.jar", "starfarer.api.jar"]
                  + [r for r in sorted(LOC) if r.endswith(".fnt")][:1])
    antigos = {}
    for r in escolhidos:
        with open(LOC[r], "rb") as f:
            antigos[r] = f.read() + b"\n#versao antiga"
    hashes_antigos = {r: [hashlib.sha256(b).hexdigest()] for r, b in antigos.items()}

    # (a) sem o backup_original da versão antiga
    for nome, executar in (("ps", ps), ("py", py)):
        d = ambiente("atual_" + nome, jogo_original)
        jogo = os.path.join(d, "starsector-core")
        registrar_anteriores(d, hashes_antigos)
        for r, b in antigos.items():
            with open(nd(jogo, r), "wb") as f:
                f.write(b)
        rc, out = executar(d, "pt")
        check(rc == 0 and "eram de uma vers" in out, f"{nome}: atualiza sem backup ({rc}) {out[-250:] if rc else ''}")
        estado(d, HL, f"{nome}: apos atualizar")
        check(not (set(antigos) & bkp(d)), f"{nome}: tradução antiga não vira 'original' no backup")
        check(not (manif(d) or {}).get("mesclados"), f"{nome}: não passa pela mescla")
        rc, out = executar(d, "en")
        ruins = [r for r in LOC if r not in antigos and sha(nd(jogo, r)) != HO[r]]
        check(rc == 0 and not ruins, f"{nome}: en devolve os demais ao original {ruins[:3]}")
        check(all(sha(nd(jogo, r)) == HL[r] for r in antigos), f"{nome}: arquivos atualizados seguem traduzidos")
        check(all(r in out for r in antigos), f"{nome}: en lista os arquivos sem original")

    # (b) zip novo extraído por cima da pasta antiga: o backup_original antigo continua lá
    d = ambiente("sobre", jogo_original)
    loc = os.path.join(d, "PTBR_Patch", "localization")
    for r, b in antigos.items():
        with open(nd(loc, r), "wb") as f:
            f.write(b)
    rc, _ = ps(d, "pt")
    check(rc == 0, "versão antiga instalada")
    for r in antigos:
        shutil.copy2(LOC[r], nd(loc, r))
    registrar_anteriores(d, hashes_antigos)
    rc, out = ps(d, "pt")
    check(rc == 0 and "eram de uma vers" not in out, f"por cima da pasta antiga: atualiza ({rc})")
    estado(d, HL, "por cima: apos atualizar")
    rc, _ = ps(d, "en")
    check(rc == 0, "por cima: en")
    estado(d, HO, "por cima: volta ao original")


def t_historico():
    print("\n== 4d. versões já publicadas (histórico do git)")
    repo = os.path.join(os.path.dirname(RAIZ_PROJ), "starsector-ptbr-github")
    if not os.path.isdir(os.path.join(repo, ".git")):
        print("PULADO  repositório do GitHub não encontrado")
        return
    pref = "kit/PTBR_Patch/localization/"
    commits = subprocess.run(["git", "-C", repo, "log", "--format=%h", "--", pref.rstrip("/")],
                             capture_output=True, text=True).stdout.split()
    check(len(commits) >= 3, f"{len(commits)} estados publicados no histórico")
    for c in commits:
        zpath = os.path.join(RAIZ, f"hist_{c}.zip")
        subprocess.run(["git", "-C", repo, "archive", "--format=zip", "-o", zpath, c, pref.rstrip("/")], check=True)
        d = ambiente("hist_" + c, jogo_original)
        jogo = os.path.join(d, "starsector-core")
        with zipfile.ZipFile(zpath) as z:
            for n in z.namelist():
                if n.endswith("/") or not n.startswith(pref):
                    continue
                rel = n[len(pref):]
                if rel in LOC:
                    with open(nd(jogo, rel), "wb") as f:
                        f.write(z.read(n))
        os.remove(zpath)
        rc, out = ps(d, "pt")
        check(rc == 0 and "n\u00e3o foram trocados" not in out and "outra vers" not in out,
              f"estado {c}: instala sem recusar ({rc}) {out[-250:] if rc else ''}")
        estado(d, HL, f"estado {c}: apos instalar")


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
        check(not any("__pycache__" in n for n in nomes), "zip sem __pycache__")
        for n in ("INSTALAR.bat", "DESINSTALAR.bat", "_instalador.ps1", "_swapLangFile.py", "README.txt",
                  "mescla.dat", "MUDANCAS.txt", "hashes_anteriores.json"):
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
        for t in (t_kit, t_original, t_python, t_traduzido, t_recusa, t_mescla, t_atualizacao, t_historico, t_versao,
                  t_permissao, t_caminho, t_zip):
            t()
    finally:
        shutil.rmtree(RAIZ, ignore_errors=True)
    print(f"\nFalhas: {len(FALHAS)}")
    for f in FALHAS:
        print("  -", f)
    sys.exit(1 if FALHAS else 0)
