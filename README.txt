TRADUÇÃO PT-BR DO STARSECTOR 0.98a-RC8

Tradução do Starsector 0.98a-RC8 para o português do Brasil, gratuita.
23.049 textos traduzidos: diálogos da campanha, descrições, menus, missões, habilidades e Codex.
Nomes de naves e armas continuam em inglês, por decisão.

DOWNLOAD
O pacote pronto para instalar (com instalador de dois cliques) está no Google Drive:
https://drive.google.com/file/d/1VUQ3XCQ6t1Lcbae3T2efDdyAKHKFxMR3/view?usp=sharing

Tópico no fórum da Fractal Softworks: (link do tópico aqui)

INSTALAÇÃO
1. Extraia o PTBR_Patch.zip dentro da pasta do Starsector, ao lado de starsector-core.
2. Dê dois cliques em PTBR_Patch\INSTALAR.bat.
3. Para voltar ao inglês, dê dois cliques em PTBR_Patch\DESINSTALAR.bat.
Instruções completas em kit/PTBR_Patch/README.txt.

O QUE TEM NESTE REPOSITÓRIO
kit/PTBR_Patch/          instalador, script Python, arquivos de dados e jars traduzidos
kit/packaging/make_kit.py   monta o kit e o zip a partir do build
units/                   textos originais (.en.json) e traduções (.pt.json), em blocos
tools/sstr.py            extrai os textos do jogo, valida as traduções e gera o build
tools/qa.py, setpt.py    verificação e edição das traduções
tools/VerifyJars.java    testa se as classes dos jars traduzidos carregam
GLOSSARIO.txt            termos usados na tradução

A pasta kit/PTBR_Patch/localization inclui os dois jars do jogo traduzidos (starfarer_obf.jar e starfarer.api.jar), com os textos de interface que ficam dentro do código. Você também pode baixar este repositório como zip (botão Code > Download ZIP) e usar a pasta kit/PTBR_Patch como o pacote do Drive.

COMO CONTRIBUIR
Encontrou um erro? Abra uma issue com o texto em inglês, o texto em português e onde ele aparece no jogo.
As traduções ficam em units/NNNN_<tipo>.pt.json. Depois de editar, rode:
       python -X utf8 tools/sstr.py validate
Para gerar o build, o sstr.py precisa dos arquivos originais do jogo e do mapa de campos do projeto chinês (ref/para_tranz_map.json), que não estão aqui.

LIMITAÇÕES
- Funciona só no Starsector 0.98a-RC8.
- Algumas fontes do jogo (futura, ursula, arial13 e arial14) não têm acentos.
- A tradução foi feita com apoio de IA e ainda não passou por revisão completa.

CRÉDITOS
- TruthOriginem e colaboradores do Starsector-Localization-CN (https://github.com/TruthOriginem/Starsector-Localization-CN): mapa de textos traduzíveis e modelo do kit.
- jar-string-decoupler 1.0.1, usado para separar os textos dos jars.
- Fractal Softworks, pelo jogo. Starsector é marca da Fractal Softworks; esta tradução não é oficial.
