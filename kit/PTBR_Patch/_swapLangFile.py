# -*- coding: utf-8 -*-
"""Troca os arquivos do Starsector entre a tradução PT-BR e o inglês original.

Coloque esta pasta (PTBR_Patch) ao lado da pasta starsector-core do jogo, no mesmo nível.

Uso:
    python -X utf8 _swapLangFile.py pt
    python -X utf8 _swapLangFile.py en
    python -X utf8 _swapLangFile.py pt --game "C:\\caminho\\starsector-core"

pt: aplica a tradução PT-BR.   en: volta para o inglês.
Antes de trocar um arquivo, o original é guardado em backup_original.
Se um arquivo do jogo tiver conteúdo diferente do original e da tradução, ele não é trocado.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

KIT = os.path.dirname(os.path.abspath(__file__))
LOC = os.path.join(KIT, "localization")
BKP = os.path.join(KIT, "backup_original")
MANIFESTO = os.path.join(BKP, "_manifesto.json")
ORIGINAIS = os.path.join(KIT, "hashes_originais.json")
MESCLA = os.path.join(KIT, "mescla.dat")
ANTERIORES = os.path.join(KIT, "hashes_anteriores.json")
VERSAO = "1.3.0"


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


def ler_json(caminho, padrao):
    if os.path.exists(caminho):
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    return padrao


def gravar_json(caminho, dados):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


_MESCLA = None


def carregar_mescla():
    """mescla.dat: para cada arquivo, chave da linha original -> linha traduzida (veja make_kit.py)."""
    global _MESCLA
    if _MESCLA is not None:
        return _MESCLA
    _MESCLA = {}
    if not os.path.exists(MESCLA):
        return _MESCLA
    with open(MESCLA, "rb") as f:
        linhas = f.read().split(b"\n")
    if linhas[0] != b"PTBR-MESCLA 1":
        return _MESCLA
    i = 1
    while i < len(linhas):
        if linhas[i].startswith(b"@"):
            rel, n = linhas[i][1:].split(b"\t")
            n = int(n)
            bloco = linhas[i + 1:i + 1 + 2 * n]
            _MESCLA[rel.decode("utf-8")] = {bloco[k].decode("ascii"): bloco[k + 1] for k in range(0, 2 * n, 2)}
            i += 1 + 2 * n
        else:
            i += 1
    return _MESCLA


def mesclar(entrada, saida, rel):
    """Traduz as linhas que continuam iguais às do original. Devolve quantas trocou; com 0 não grava."""
    mapa = carregar_mescla().get(rel)
    if not mapa:
        return 0
    with open(entrada, "rb") as f:
        linhas = f.read().split(b"\n")
    trocadas = 0
    for j, linha in enumerate(linhas):
        cr = linha.endswith(b"\r")
        corpo = linha[:-1] if cr else linha
        if not corpo:
            continue
        alvo = mapa.get(hashlib.sha256(corpo).hexdigest()[:16])
        if alvo is not None:
            linhas[j] = alvo + (b"\r" if cr else b"")
            trocadas += 1
    if trocadas:
        with open(saida, "wb") as f:
            f.write(b"\n".join(linhas))
    return trocadas


def aplicar_pt(jogo):
    originais = ler_json(ORIGINAIS, {})
    manifesto = ler_json(MANIFESTO, {"novos": []})
    mesclados = list(manifesto.get("mesclados", []))
    anteriores = ler_json(ANTERIORES, {})
    atualizados = []
    recusados = []
    parciais = []
    trocados = 0
    for rel in arquivos_em(LOC):
        origem = no_disco(LOC, rel)
        destino = no_disco(jogo, rel)
        guardado = no_disco(BKP, rel)
        if rel in mesclados and os.path.exists(guardado):
            # já foi traduzido em parte: refaz a partir da versão do outro mod guardada no backup
            parciais.append((rel, mesclar(guardado, destino, rel)))
            trocados += 1
            continue
        if os.path.exists(destino):
            atual = sha256(destino)
            if atual == sha256(origem):
                pass  # o jogo já tem esta tradução
            elif atual == originais.get(rel):
                if not os.path.exists(guardado):
                    os.makedirs(os.path.dirname(guardado), exist_ok=True)
                    shutil.copy2(destino, guardado)  # guarda o original antes de trocar
            elif not os.path.exists(guardado) and atual in anteriores.get(rel, []):
                # tradução de uma versão anterior deste kit, e o backup_original dela não existe mais:
                # atualiza direto. Não é "outro mod", então não passa pela mescla.
                atualizados.append(rel)
                shutil.copy2(origem, destino)
                trocados += 1
                continue
            elif not os.path.exists(guardado):
                # alterado por outro mod: traduz só as linhas que continuam iguais às do original
                temp = destino + ".ptbr_tmp"
                n = mesclar(destino, temp, rel)
                if n == 0:
                    recusados.append(rel)
                    continue
                os.makedirs(os.path.dirname(guardado), exist_ok=True)
                shutil.copy2(destino, guardado)
                os.replace(temp, destino)
                mesclados.append(rel)
                parciais.append((rel, n))
                trocados += 1
                continue
        elif rel not in manifesto["novos"]:
            manifesto["novos"].append(rel)  # arquivo novo: a volta ao inglês remove
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        shutil.copy2(origem, destino)
        trocados += 1
    if mesclados:
        manifesto["mesclados"] = mesclados
    gravar_json(MANIFESTO, manifesto)
    return trocados, recusados, parciais, atualizados


def versao_compativel(jogo):
    """O jar principal precisa ser o original da 0.98.5a-RC4, o traduzido, ou já ter original guardado."""
    original = ler_json(ORIGINAIS, {}).get("starfarer_obf.jar")
    if not original:
        return True
    atual = sha256(os.path.join(jogo, "starfarer_obf.jar"))
    traduzido = os.path.join(LOC, "starfarer_obf.jar")
    return (atual == original
            or (os.path.exists(traduzido) and atual == sha256(traduzido))
            or os.path.exists(os.path.join(BKP, "starfarer_obf.jar"))
            or atual in ler_json(ANTERIORES, {}).get("starfarer_obf.jar", []))  # jar de uma versão anterior do kit


def voltar_en(jogo):
    manifesto = ler_json(MANIFESTO, {"novos": []})
    restaurados = 0
    if os.path.isdir(BKP):
        for rel in arquivos_em(BKP):
            if rel == "_manifesto.json":
                continue
            destino = no_disco(jogo, rel)
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            shutil.copy2(no_disco(BKP, rel), destino)
            restaurados += 1
    for rel in manifesto.get("mesclados", []):
        # a cópia guardada é a versão do outro mod, já devolvida ao jogo; sem ela, a próxima instalação mescla de novo
        guardado = no_disco(BKP, rel)
        if os.path.exists(guardado):
            os.remove(guardado)
    removidos = 0
    for rel in manifesto["novos"]:
        destino = no_disco(jogo, rel)
        if os.path.exists(destino):
            os.remove(destino)
            removidos += 1
    sem_original = [
        rel
        for rel in arquivos_em(LOC)
        if not os.path.exists(no_disco(BKP, rel)) and rel not in manifesto["novos"]
        and rel not in manifesto.get("mesclados", [])
    ]
    if os.path.exists(MANIFESTO):
        os.remove(MANIFESTO)
    return restaurados, removidos, sem_original


def main():
    parser = argparse.ArgumentParser(
        description="Troca a tradução PT-BR e o inglês do Starsector 0.98.5a-RC4."
    )
    parser.add_argument(
        "acao", nargs="?", choices=["pt", "en"],
        help="pt = aplicar a tradução; en = voltar ao inglês",
    )
    parser.add_argument(
        "--game", help="pasta starsector-core, se não estiver ao lado desta pasta"
    )
    args = parser.parse_args()
    print(f"Tradução PT-BR do Starsector 0.98.5a-RC4 (kit v{VERSAO})")

    jogo = args.game or os.path.normpath(os.path.join(KIT, "..", "starsector-core"))
    if not os.path.isfile(os.path.join(jogo, "starfarer_obf.jar")):
        print("Não encontrei o jogo em:", jogo)
        print('Coloque esta pasta ao lado de starsector-core, ou use --game "caminho\\starsector-core".')
        return 1

    acao = args.acao or input("Digite pt para aplicar a tradução ou en para voltar ao inglês: ").strip().lower()
    if acao == "pt":
        if not os.path.isdir(LOC):
            print("Pasta localization não encontrada.")
            return 1
        if not versao_compativel(jogo):
            print("Este kit é para o Starsector 0.98.5a-RC4, e o seu jogo parece ser de outra versão")
            print("(o arquivo starfarer_obf.jar não é o da 0.98.5a-RC4). Nada foi alterado.")
            return 1
        try:
            trocados, recusados, parciais, atualizados = aplicar_pt(jogo)
        except PermissionError as e:
            print("Sem permissão para gravar:", e.filename)
            print("Rode o terminal como administrador (Windows) ou com sudo (Linux), ou mova o jogo para uma pasta sua.")
            print("Os arquivos já trocados têm o original guardado em backup_original; rodar de novo é seguro.")
            return 1
        print(f"{trocados} arquivo(s) traduzido(s) aplicado(s) em {jogo}")
        print("Originais guardados em backup_original (não apague essa pasta).")
        if atualizados:
            print(f"{len(atualizados)} arquivo(s) eram de uma versão anterior da tradução e foram atualizados.")
            print("Não encontrei o backup_original da versão antiga, então esses arquivos não têm original guardado:")
            print("o modo en não consegue voltá-los ao inglês. Para isso, use a verificação de integridade do jogo (Steam).")
            print("Na próxima atualização, extraia o zip por cima da pasta PTBR_Patch antiga.")
        if parciais:
            print(f"{len(parciais)} arquivo(s) alterado(s) por outro mod foram traduzidos em parte:")
            for rel, n in parciais[:30]:
                print(f"    {rel} ({n} linhas)")
            print("As mudanças do outro mod foram mantidas. Os textos que ele trocou continuam em inglês.")
        if recusados:
            print(f"{len(recusados)} arquivo(s) não foram trocados, porque o conteúdo é diferente do original e da tradução:")
            for rel in recusados[:30]:
                print("   ", rel)
            print("Restaure os originais do jogo e rode o script de novo.")
            return 1
        return 0
    if acao == "en":
        restaurados, removidos, sem_original = voltar_en(jogo)
        print(f"{restaurados} arquivo(s) original(is) restaurado(s), {removidos} arquivo(s) novo(s) removido(s).")
        if sem_original:
            print(f"{len(sem_original)} arquivo(s) não tinham original guardado e continuam como estão:")
            for rel in sem_original[:30]:
                print("   ", rel)
        return 0
    print("Opção inválida. Use pt ou en.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
