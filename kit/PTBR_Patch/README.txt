TRADUÇÃO PT-BR DO STARSECTOR 0.98a-RC8 (KIT DE PATCH v1.2.0)
As mudanças de cada versão estão em MUDANCAS.txt.

O QUE É
Este kit troca arquivos do jogo pelos arquivos traduzidos. Antes de trocar, o script guarda os originais na pasta backup_original e volta ao inglês quando você pedir. Não apague a pasta backup_original.

O kit inclui os arquivos de dados traduzidos e os dois jars do jogo traduzidos (starfarer_obf.jar e starfarer.api.jar), que levam os textos de interface que ficam dentro do código.

REQUISITOS
- Starsector 0.98a-RC8. Outras versões não são suportadas.
- Windows 10 ou 11 para o instalador. Em Linux ou macOS, use o script Python (veja abaixo).

INSTALAÇÃO (WINDOWS)
Feche o jogo antes de começar.
1. Extraia o PTBR_Patch.zip dentro da pasta do Starsector, para que a pasta PTBR_Patch fique ao lado de starsector-core. Exemplo:
       C:\Program Files (x86)\Fractal Softworks\Starsector\starsector-core
       C:\Program Files (x86)\Fractal Softworks\Starsector\PTBR_Patch
2. Dê dois cliques em PTBR_Patch\INSTALAR.bat.
3. Abra o jogo normalmente.

Se o instalador não achar o jogo, ele abre uma janela para você escolher a pasta do Starsector.
Se o jogo estiver em Arquivos de Programas, o Windows pede permissão de administrador. Isso é normal: a pasta do jogo é protegida.
Se mesmo assim aparecer "acesso negado", clique com o botão direito em INSTALAR.bat e escolha "Executar como administrador".
O instalador só funciona no Starsector 0.98a-RC8; em outra versão ele avisa e não altera nada.

VOLTAR AO INGLÊS
Dê dois cliques em PTBR_Patch\DESINSTALAR.bat.
Isso restaura os arquivos guardados em backup_original. Se o jogo já estava traduzido antes de você aplicar o kit, não há originais guardados: o instalador informa quais arquivos continuam com a tradução. Nesse caso, use uma cópia dos originais feita antes.

LINUX, MACOS OU PYTHON
Com Python 3 instalado, rode dentro da pasta PTBR_Patch:
       python3 -X utf8 _swapLangFile.py pt      (aplica a tradução)
       python3 -X utf8 _swapLangFile.py en      (volta ao inglês)
Se a pasta do jogo estiver em outro lugar, acrescente --game "caminho" apontando para a pasta que contém starfarer_obf.jar.
Linux e macOS não foram testados.
O instalador e o script Python usam o mesmo backup e podem ser usados no mesmo jogo.

INSTALAÇÃO MANUAL (SEM PYTHON)
Antes de começar, faça uma cópia da pasta starsector-core. Depois copie o conteúdo de PTBR_Patch\localization para dentro de starsector-core, aceitando substituir os arquivos. Para voltar, use a cópia.

ATUALIZAR DE UMA VERSÃO ANTERIOR
Extraia o zip novo por cima da pasta PTBR_Patch antiga, aceitando substituir os arquivos, e dê dois cliques em INSTALAR.bat. A pasta backup_original é mantida, então o DESINSTALAR.bat continua voltando ao inglês.
Se você apagou a pasta antiga, o instalador ainda reconhece a tradução das versões anteriores e atualiza os arquivos. Nesse caso os originais não estão guardados: para voltar ao inglês, use a verificação de integridade do jogo (Steam).

ARQUIVOS ALTERADOS POR OUTRO MOD
Se outro mod ou patch já alterou um arquivo do jogo, o instalador traduz só as linhas que continuam iguais às do original e mantém as mudanças do outro mod. Os textos que o outro mod trocou continuam em inglês. O instalador mostra esses arquivos como "traduzidos em parte". O DESINSTALAR.bat devolve a versão do outro mod.

SE O SCRIPT RECUSAR ARQUIVOS
Ele recusa um arquivo quando o conteúdo é diferente do original e da tradução e nenhuma linha pode ser traduzida, por exemplo um dos dois jars alterado por outro patch. Restaure os originais do jogo (com a cópia feita antes ou, se o jogo for da Steam, pela verificação de integridade) e rode o script de novo.

LIMITAÇÕES CONHECIDAS
- Oito fontes do jogo não tinham letras acentuadas (arial13, arial14, futura12, futura16, insignia12, ursula12, ursula14 e ursula16). O kit inclui versões dessas fontes com os acentos montados a partir de sinais que já existem na própria fonte; eles podem ficar um pouco diferentes do resto da letra.
- Alguns textos continuam em inglês por decisão: linhas de depuração e teste do desenvolvedor, e nomes de naves e armas.
- A tradução foi feita com apoio de IA e ainda não passou por revisão completa. Se encontrar erros, avise.

CRÉDITOS
A lista de campos traduzíveis segue a abordagem do projeto TruthOriginem/Starsector-Localization-CN, que também inspirou o formato deste kit. Os textos dos jars foram separados do código com a ferramenta jar-string-decoupler 1.0.1.
