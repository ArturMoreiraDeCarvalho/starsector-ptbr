TRADUÇÃO PT-BR DO STARSECTOR 0.98a-RC8

Tradução do Starsector 0.98a-RC8 para o português do Brasil, gratuita.
23.049 textos traduzidos: diálogos da campanha, descrições, menus, missões, habilidades e Codex.
Inclui as fontes do jogo com letras acentuadas.
Nomes de naves e armas continuam em inglês, por decisão.

Menu principal com a tradução: imagens/menu_ptbr.png

DOWNLOAD
Pacote pronto para instalar (com instalador de dois cliques):
https://drive.google.com/file/d/1VUQ3XCQ6t1Lcbae3T2efDdyAKHKFxMR3/view?usp=sharing
Ou baixe este repositório (Code > Download ZIP) e use a pasta kit/PTBR_Patch.

Tópico no fórum da Fractal Softworks: (link do tópico aqui)

INSTALAÇÃO
1. Feche o jogo. Coloque a pasta PTBR_Patch dentro da pasta do Starsector, ao lado de starsector-core.
2. Dê dois cliques em PTBR_Patch\INSTALAR.bat. Se o jogo estiver em Arquivos de Programas,
   o Windows pede permissão de administrador.
3. Para voltar ao inglês, dê dois cliques em PTBR_Patch\DESINSTALAR.bat.
Instruções completas em kit/PTBR_Patch/README.txt.

O QUE TEM NESTE REPOSITÓRIO
kit/PTBR_Patch/             instalador, script Python e arquivos traduzidos (dados, jars e fontes)
kit/packaging/make_kit.py   monta o kit e o zip a partir do build
kit/packaging/teste_kit.py  testes do instalador em cópias temporárias
units/                      textos originais (.en.json) e traduções (.pt.json), em blocos
tools/sstr.py               extrai os textos do jogo, valida as traduções e gera o build
tools/fontfix.py            adiciona letras acentuadas às fontes bitmap do jogo
tools/glossario.py          lista textos que fogem dos termos do GLOSSARIO.txt
tools/qa.py, setpt.py       verificação e edição das traduções
tools/VerifyJars.java       testa se as classes dos jars traduzidos carregam
GLOSSARIO.txt               termos usados na tradução
COMO_ATUALIZAR.txt          passo a passo para gerar o kit de uma versão nova do jogo

A pasta kit/PTBR_Patch/localization inclui os dois jars do jogo traduzidos (starfarer_obf.jar e
starfarer.api.jar), com os textos de interface que ficam dentro do código, e as fontes alteradas.

COMO CONTRIBUIR
Encontrou um erro? Abra uma issue com o texto em inglês, o texto em português e onde ele aparece no jogo.
As traduções ficam em units/NNNN_<tipo>.pt.json. Depois de editar, rode:
       python -X utf8 tools/sstr.py validate
       python -X utf8 tools/glossario.py
Para gerar o build, o sstr.py precisa dos arquivos originais do jogo e do mapa de campos do projeto
chinês (ref/para_tranz_map.json), que não estão aqui. Veja COMO_ATUALIZAR.txt.

LIMITAÇÕES
- Funciona só no Starsector 0.98a-RC8. Em outra versão, o instalador avisa e não altera nada.
- Os acentos das nove fontes que não os tinham foram desenhados à mão e podem destoar um pouco da letra.
- A tradução foi feita com apoio de IA e ainda não passou por revisão completa.
- Textos de mods não são traduzidos; compatibilidade com mods não testada.
- Linux e macOS (script Python) não foram testados.

CRÉDITOS
- TruthOriginem e colaboradores do Starsector-Localization-CN (https://github.com/TruthOriginem/Starsector-Localization-CN):
  mapa de textos traduzíveis e modelo do kit.
- jar-string-decoupler 1.0.1, usado para separar os textos dos jars.
- Fractal Softworks, pelo jogo. Starsector é marca da Fractal Softworks; esta tradução não é oficial.
