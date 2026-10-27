# -*- coding: utf-8 -*-
"""Adiciona letras acentuadas às fontes bitmap (BMFont .fnt + .png) do Starsector que só têm ASCII.

Os glifos novos são montados com peças da própria fonte, para manter o estilo:
  grave = `   agudo = ` espelhado   circunflexo = ^   til = ~   cedilha = vírgula
Lê os originais em backup/graphics/fonts e grava em build/graphics/fonts.

Uso:
    python -X utf8 tools/fontfix.py            gera as fontes
    python -X utf8 tools/fontfix.py preview    gera também test/fontes_preview.png
"""
import os
import re
import shutil
import sys

from PIL import Image, ImageDraw

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(RAIZ, "backup", "graphics", "fonts")
SAIDA = os.path.join(RAIZ, "build", "graphics", "fonts")
# de onde copiar as fontes originais na primeira execução (pasta starsector-core de um jogo em inglês)
JOGO_CORE = os.environ.get("STARSECTOR_CORE", r"C:\Program Files (x86)\Fractal Softworks\Starsector\starsector-core")
JOGO_FONTES = os.path.join(JOGO_CORE, "graphics", "fonts")

# letras usadas na tradução (todas as que aparecem em units/*.pt.json)
ACENTOS = {
    "à": ("a", "grave"), "á": ("a", "agudo"), "â": ("a", "circ"), "ã": ("a", "til"),
    "é": ("e", "agudo"), "è": ("e", "grave"), "ê": ("e", "circ"),
    "í": ("i", "agudo"), "ó": ("o", "agudo"), "ô": ("o", "circ"), "õ": ("o", "til"),
    "ú": ("u", "agudo"), "ç": ("c", "cedilha"),
    "À": ("A", "grave"), "Á": ("A", "agudo"), "Â": ("A", "circ"), "Ã": ("A", "til"),
    "É": ("E", "agudo"), "Ê": ("E", "circ"), "Í": ("I", "agudo"), "Ó": ("O", "agudo"),
    "Ô": ("O", "circ"), "Õ": ("O", "til"), "Ú": ("U", "agudo"), "Ç": ("C", "cedilha"),
}
EXTRAS = {"ª": "a", "º": "o", "×": "x", "–": "-", "“": '"', "”": '"'}
NECESSARIOS = list(ACENTOS) + list(EXTRAS)


# ------------------------------------------------------------------ leitura e escrita do .fnt
def ler_fnt(caminho):
    with open(caminho, encoding="utf-8-sig") as f:
        linhas = f.read().splitlines()
    chars = {}
    common = page = None
    for i, ln in enumerate(linhas):
        tag = ln.split(" ", 1)[0]
        attrs = dict(re.findall(r'(\w+)=("[^"]*"|\S+)', ln))
        if tag == "char":
            chars[int(attrs["id"])] = {k: int(v) for k, v in attrs.items() if k in
                                       ("x", "y", "width", "height", "xoffset", "yoffset", "xadvance", "page", "chnl")}
        elif tag == "common":
            common = (i, {k: v for k, v in attrs.items()})
        elif tag == "page":
            page = attrs["file"].strip('"')
    return linhas, chars, common, page


def recorte(atlas, c):
    return atlas.crop((c["x"], c["y"], c["x"] + c["width"], c["y"] + c["height"]))


def aparar(img):
    """Recorta a área com tinta; devolve (imagem, dx, dy) ou None."""
    caixa = img.getchannel("A").getbbox()
    if not caixa:
        return None
    return img.crop(caixa), caixa[0], caixa[1]


def sem_pingo(img):
    """Tira o pingo do i: corta as linhas de cima até a primeira linha vazia."""
    a = img.getchannel("A")
    w, h = img.size
    cheias = [any(a.getpixel((x, y)) > 40 for x in range(w)) for y in range(h)]
    if True not in cheias:
        return img, 0
    y = cheias.index(True)
    while y < h and cheias[y]:
        y += 1
    while y < h and not cheias[y]:
        y += 1
    if y >= h:
        return img, 0
    return img.crop((0, y, w, h)), y


def escalar(img, max_w, max_h):
    w, h = img.size
    f = min(1.0, max_w / w, max_h / h)
    if f >= 1.0:
        return img
    return img.resize((max(1, round(w * f)), max(1, round(h * f))), Image.LANCZOS)


# ------------------------------------------------------------------ montagem
class Fonte:
    def __init__(self, nome):
        self.nome = nome
        self.linhas, self.chars, self.common, self.page = ler_fnt(os.path.join(ORIG, nome + ".fnt"))
        self.atlas = Image.open(os.path.join(ORIG, self.page)).convert("RGBA")
        self.line_h = int(self.common[1]["lineHeight"])
        self.base = int(self.common[1]["base"])

    def glifo(self, ch):
        c = self.chars.get(ord(ch))
        if not c or c["width"] == 0 or c["height"] == 0:
            return None
        return recorte(self.atlas, c), c

    def espessura(self):
        """Largura do traço vertical da fonte, medida na letra l."""
        g = self.glifo("l") or self.glifo("I")
        if not g:
            return 1.0
        a = g[0].getchannel("A")
        w, h = a.size
        soma = sum(a.getpixel((x, h // 2)) for x in range(w)) / 255.0
        return max(1.0, min(3.0, soma))

    PADROES = {
        "agudo": ["..#", ".#.", "#.."],
        "grave": ["#..", ".#.", "..#"],
        "circ": [".#.", "#.#"],
        "til": [".#..#", "#.##."],
        "cedilha": [".#.", "..#", "##."],
    }

    def diacritico(self, tipo, maiuscula):
        """Acento em pixel art, no estilo das fontes bitmap; fontes grandes usam o padrão ampliado."""
        pad = list(self.PADROES[tipo])
        if tipo in ("agudo", "grave") and (maiuscula or self.line_h < 14):
            pad = pad[:2] if tipo == "grave" else pad[1:]
        k = max(1, round(self.line_h / 16))
        grosso = self.espessura() >= 1.8
        h, w = len(pad), len(pad[0]) + (1 if grosso else 0)
        img = Image.new("RGBA", (w, h), (255, 255, 255, 0))
        for y, linha in enumerate(pad):
            for x, c in enumerate(linha):
                if c == "#":
                    img.putpixel((x, y), (255, 255, 255, 255))
                    if grosso:
                        img.putpixel((x + 1, y), (255, 255, 255, 255))
        if k > 1:
            img = img.resize((w * k, h * k), Image.NEAREST)
        return img

    def compor(self, ch):
        """Devolve (imagem, xoffset, yoffset, xadvance) do glifo novo, ou None."""
        if ch in ACENTOS:
            letra, tipo = ACENTOS[ch]
            g = self.glifo(letra)
            if not g:
                return None
            base_img, bc = g
            bx, by = bc["xoffset"], bc["yoffset"]
            if letra == "i":
                base_img, corte = sem_pingo(base_img)
                by += corte
            ac = self.diacritico(tipo, letra.isupper())
            if ac is None:
                return None
            ap = aparar(base_img)
            tinta_x0, tinta_y0 = (bx + ap[1], by + ap[2]) if ap else (bx, by)
            tinta_w = ap[0].size[0] if ap else base_img.size[0]
            tinta_y1 = tinta_y0 + (ap[0].size[1] if ap else base_img.size[1])
            ax = tinta_x0 + (tinta_w - ac.size[0] + 1) // 2
            if tipo == "cedilha":
                ay = tinta_y1 - 1
            else:
                ay = tinta_y0 - 1 - ac.size[1]
            return self._juntar([(base_img, bx, by), (ac, ax, ay)], bc["xadvance"])
        letra = EXTRAS[ch]
        g = self.glifo(letra)
        if not g:
            return None
        img, c = g
        if ch in "ªº":
            ap = aparar(img)
            if not ap:
                return None
            peq = escalar(ap[0], ap[0].size[0], max(2, round(ap[0].size[1] * 0.6)))
            topo = self.base - round(self.line_h * 0.62)
            x0 = c["xoffset"] + ap[1]
            traco = Image.new("RGBA", (peq.size[0], 1), (255, 255, 255, 255))
            return self._juntar([(peq, x0, topo), (traco, x0, topo + peq.size[1] + 1)], max(peq.size[0] + 2, 3))
        if ch == "–":
            ap = aparar(img)
            if not ap:
                return None
            n = self.chars.get(ord("n"))
            larg = max(ap[0].size[0] + 2, (n["xadvance"] - 1) if n else ap[0].size[0] * 2)
            esticado = ap[0].resize((larg, ap[0].size[1]), Image.LANCZOS)
            return self._juntar([(esticado, c["xoffset"] + ap[1], c["yoffset"] + ap[2])], larg + 2)
        return img.copy(), c["xoffset"], c["yoffset"], c["xadvance"]

    @staticmethod
    def _juntar(pecas, xadvance):
        x0 = min(x for _, x, _ in pecas)
        y0 = min(y for _, _, y in pecas)
        x1 = max(x + im.size[0] for im, x, _ in pecas)
        y1 = max(y + im.size[1] for im, _, y in pecas)
        tela = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
        for im, x, y in pecas:
            camada = Image.new("RGBA", tela.size, (0, 0, 0, 0))
            camada.paste(im, (x - x0, y - y0))
            tela = Image.alpha_composite(tela, camada)
        return tela, x0, y0, xadvance

    def faltando(self):
        return [ch for ch in NECESSARIOS if ord(ch) not in self.chars]

    def gerar(self):
        novos = []
        for ch in self.faltando():
            r = self.compor(ch)
            if r:
                novos.append((ch, r))
        if not novos:
            return 0
        # empacota em prateleiras abaixo do atlas original; altura final em potência de 2
        w_atlas, h_atlas = self.atlas.size
        x, y, alt_linha = 1, h_atlas + 1, 0
        posicoes = []
        for ch, (img, xo, yo, xa) in novos:
            iw, ih = img.size
            if x + iw + 1 > w_atlas:
                x, y, alt_linha = 1, y + alt_linha + 1, 0
            posicoes.append((ch, img, x, y, xo, yo, xa))
            x += iw + 1
            alt_linha = max(alt_linha, ih)
        altura = h_atlas
        while altura < y + alt_linha + 1:
            altura *= 2
        atlas = Image.new("RGBA", (w_atlas, altura), (0, 0, 0, 0))
        atlas.paste(self.atlas, (0, 0))
        linhas_char = []
        for ch, img, px, py, xo, yo, xa in posicoes:
            atlas.paste(img, (px, py))
            linhas_char.append(
                f"char id={ord(ch):<4} x={px:<5} y={py:<5} width={img.size[0]:<5} height={img.size[1]:<5} "
                f"xoffset={xo:<5} yoffset={yo:<5} xadvance={xa:<5} page=0  chnl=15")
        linhas = list(self.linhas)
        i, _ = self.common
        linhas[i] = re.sub(r"scaleH=\d+", f"scaleH={altura}", linhas[i])
        ultimo = max(k for k, ln in enumerate(linhas) if ln.startswith("char "))
        linhas[ultimo + 1:ultimo + 1] = linhas_char
        total = len(self.chars) + len(linhas_char)
        linhas = [re.sub(r"^chars count=\d+", f"chars count={total}", ln) for ln in linhas]
        os.makedirs(SAIDA, exist_ok=True)
        with open(os.path.join(SAIDA, self.nome + ".fnt"), "w", encoding="utf-8", newline="\r\n") as f:
            f.write("\n".join(linhas) + "\n")
        atlas.save(os.path.join(SAIDA, self.page))
        return len(novos)


# ------------------------------------------------------------------ prévia
def renderizar(dir_fontes, nome, texto, escala=3):
    linhas, chars, common, page = ler_fnt(os.path.join(dir_fontes, nome + ".fnt"))
    atlas = Image.open(os.path.join(dir_fontes, page)).convert("RGBA")
    lh = int(common[1]["lineHeight"])
    largura = sum(chars.get(ord(c), chars.get(63, {"xadvance": 6}))["xadvance"] for c in texto) + 4
    tela = Image.new("RGBA", (largura, lh + 10), (20, 24, 40, 255))
    x = 2
    for c in texto:
        g = chars.get(ord(c))
        if g is None:
            ImageDraw.Draw(tela).rectangle((x, 2, x + 4, lh), outline=(255, 60, 60, 255))
            x += 6
            continue
        if g["width"] and g["height"]:
            tela.alpha_composite(recorte(atlas, g), (x + g["xoffset"], 6 + g["yoffset"]))
        x += g["xadvance"]
    return tela.resize((tela.size[0] * escala, tela.size[1] * escala), Image.NEAREST)


def preview(nomes):
    texto = "ÁÉÍÓÚ ÀÂÊÔ ÃÕ Ç  áéíóú àâêô ãõ ç  1ª 2º 3×4 – “ok”  Ação, São, Ônibus, Índice, missão"
    blocos = []
    for nome in nomes:
        for pasta, rot in ((ORIG, "antes"), (SAIDA, "depois")):
            img = renderizar(pasta, nome, texto)
            rotulo = Image.new("RGBA", (img.size[0], 14), (0, 0, 0, 255))
            ImageDraw.Draw(rotulo).text((2, 1), f"{nome} ({rot})", fill=(255, 255, 0, 255))
            blocos += [rotulo, img]
    larg = max(b.size[0] for b in blocos)
    alt = sum(b.size[1] for b in blocos) + 2 * len(blocos)
    tela = Image.new("RGBA", (larg, alt), (0, 0, 0, 255))
    y = 0
    for b in blocos:
        tela.paste(b, (0, y))
        y += b.size[1] + 2
    destino = os.path.join(RAIZ, "test", "fontes_preview.png")
    tela.save(destino)
    return destino


def main():
    if not os.path.isdir(ORIG):
        # primeira vez: guarda os originais das fontes junto com os outros originais
        if not os.path.isdir(JOGO_FONTES):
            raise SystemExit(f"Fontes originais não encontradas em {JOGO_FONTES}. "
                             "Defina STARSECTOR_CORE com a pasta starsector-core de um jogo em inglês.")
        shutil.copytree(JOGO_FONTES, ORIG)
    alteradas = []
    for arq in sorted(os.listdir(ORIG)):
        if not arq.endswith(".fnt"):
            continue
        nome = arq[:-4]
        f = Fonte(nome)
        falt = f.faltando()
        n = f.gerar()
        if n:
            alteradas.append(nome)
            print(f"{nome:26} faltavam {len(falt):2}  criados {n:2}")
    print(len(alteradas), "fontes alteradas")
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        print("prévia:", preview(alteradas))


if __name__ == "__main__":
    main()
