# Instalador da tradução PT-BR do Starsector 0.98.5a-RC4.
# Use INSTALAR.bat e DESINSTALAR.bat; este arquivo faz o trabalho.
# Mesma lógica e mesmo backup do _swapLangFile.py: os dois podem ser usados no mesmo jogo.
param(
    [Parameter(Mandatory = $true)][ValidateSet("pt", "en")][string]$Acao,
    [string]$Jogo,
    [switch]$SemPausa,
    [switch]$SemElevar   # só para testes: não abre o pedido de administrador
)

$ErrorActionPreference = "Stop"
$Kit = Split-Path -Parent $MyInvocation.MyCommand.Path
$Loc = Join-Path $Kit "localization"
$Bkp = Join-Path $Kit "backup_original"
$Manifesto = Join-Path $Bkp "_manifesto.json"
$ArqHashes = Join-Path $Kit "hashes_originais.json"
$ArqMescla = Join-Path $Kit "mescla.dat"
$ArqAnteriores = Join-Path $Kit "hashes_anteriores.json"
$Versao = "1.3.0"
$Utf8 = New-Object System.Text.UTF8Encoding($false)
$Latin1 = [System.Text.Encoding]::GetEncoding(28591)   # 1 byte = 1 caractere: preserva os bytes do arquivo

function Sair([int]$codigo) {
    if (-not $SemPausa) { Write-Host ""; Read-Host "Pressione Enter para fechar" | Out-Null }
    exit $codigo
}

function Hash([string]$caminho) {
    (Get-FileHash -LiteralPath $caminho -Algorithm SHA256).Hash.ToLowerInvariant()
}

function NoDisco([string]$raiz, [string]$rel) {
    Join-Path $raiz ($rel -replace "/", "\")
}

function ArquivosEm([string]$raiz) {
    if (-not (Test-Path -LiteralPath $raiz)) { return @() }
    $base = (Resolve-Path -LiteralPath $raiz).ProviderPath.TrimEnd("\")
    @(Get-ChildItem -LiteralPath $base -Recurse -File -Force |
        ForEach-Object { $_.FullName.Substring($base.Length + 1) -replace "\\", "/" } |
        Sort-Object)
}

function Copiar([string]$origem, [string]$destino) {
    $pasta = Split-Path -Parent $destino
    if (-not (Test-Path -LiteralPath $pasta)) { New-Item -ItemType Directory -Path $pasta -Force | Out-Null }
    Copy-Item -LiteralPath $origem -Destination $destino -Force
}

function LerManifesto([string]$campo) {
    if (-not (Test-Path -LiteralPath $Manifesto)) { return @() }
    $dados = [System.IO.File]::ReadAllText($Manifesto, $Utf8) | ConvertFrom-Json
    @($dados.$campo | Where-Object { $_ })
}

function LerNovos { LerManifesto "novos" }

function ListaJson([string[]]$itens) {
    '[' + (@($itens | ForEach-Object { '"' + ($_ -replace '\\', '\\' -replace '"', '\"') + '"' }) -join ", ") + ']'
}

function GravarManifesto([string[]]$novos, [string[]]$mesclados) {
    if (-not (Test-Path -LiteralPath $Bkp)) { New-Item -ItemType Directory -Path $Bkp -Force | Out-Null }
    $json = '{"novos": ' + (ListaJson $novos)
    if ($mesclados.Count -gt 0) { $json += ', "mesclados": ' + (ListaJson $mesclados) }
    [System.IO.File]::WriteAllText($Manifesto, $json + '}', $Utf8)
}

# ---------------------------------------------------------------- mescla
# Arquivo alterado por outro mod: troca só as linhas que continuam iguais às do jogo original.
$script:IndiceMescla = $null
$script:LinhasMescla = $null
$script:Sha = [System.Security.Cryptography.SHA256]::Create()

function CarregarMescla {
    if ($null -ne $script:IndiceMescla) { return }
    $script:IndiceMescla = @{}
    if (-not (Test-Path -LiteralPath $ArqMescla)) { return }
    $script:LinhasMescla = $Latin1.GetString([System.IO.File]::ReadAllBytes($ArqMescla)).Split([char]10)
    if ($script:LinhasMescla[0] -ne "PTBR-MESCLA 1") { $script:IndiceMescla = @{}; return }
    $i = 1
    while ($i -lt $script:LinhasMescla.Length) {
        $l = $script:LinhasMescla[$i]
        if ($l.StartsWith("@")) {
            $partes = $l.Substring(1).Split([char]9)
            $rel = $Utf8.GetString($Latin1.GetBytes($partes[0]))
            $n = [int]$partes[1]
            $script:IndiceMescla[$rel] = @(($i + 1), $n)
            $i += 1 + 2 * $n
        } else {
            $i++
        }
    }
}

function ChaveLinha([string]$linha) {
    $h = $script:Sha.ComputeHash($Latin1.GetBytes($linha))
    ([System.BitConverter]::ToString($h, 0, 8) -replace "-", "").ToLowerInvariant()
}

function Mesclar([string]$entrada, [string]$saida, [string]$rel) {
    # devolve quantas linhas foram traduzidas; com 0, não grava nada
    CarregarMescla
    if (-not $script:IndiceMescla.ContainsKey($rel)) { return 0 }
    $ini, $n = $script:IndiceMescla[$rel]
    $mapa = @{}
    for ($k = 0; $k -lt $n; $k++) {
        $mapa[$script:LinhasMescla[$ini + 2 * $k]] = $script:LinhasMescla[$ini + 2 * $k + 1]
    }
    $linhas = $Latin1.GetString([System.IO.File]::ReadAllBytes($entrada)).Split([char]10)
    $trocadas = 0
    for ($j = 0; $j -lt $linhas.Length; $j++) {
        $l = $linhas[$j]
        $cr = $l.EndsWith([string][char]13)
        if ($cr) { $l = $l.Substring(0, $l.Length - 1) }
        if ($l.Length -eq 0) { continue }
        $chave = ChaveLinha $l
        if ($mapa.ContainsKey($chave)) {
            $linhas[$j] = $mapa[$chave] + $(if ($cr) { [string][char]13 } else { "" })
            $trocadas++
        }
    }
    if ($trocadas -gt 0) {
        [System.IO.File]::WriteAllBytes($saida, $Latin1.GetBytes([string]::Join([string][char]10, $linhas)))
    }
    return $trocadas
}

function EhJogo([string]$pasta) {
    $pasta -and (Test-Path -LiteralPath (Join-Path $pasta "starfarer_obf.jar"))
}

function NormalizarJogo([string]$pasta) {
    if (-not $pasta) { return $null }
    if (EhJogo $pasta) { return $pasta }
    $core = Join-Path $pasta "starsector-core"
    if (EhJogo $core) { return $core }
    return $null
}

function AcharJogo {
    $candidatos = @(
        (Join-Path (Split-Path -Parent $Kit) "starsector-core"),
        (Split-Path -Parent $Kit),
        (Join-Path (Split-Path -Parent (Split-Path -Parent $Kit)) "starsector-core"),
        "${env:ProgramFiles(x86)}\Fractal Softworks\Starsector\starsector-core",
        "$env:ProgramFiles\Fractal Softworks\Starsector\starsector-core"
    )
    foreach ($c in $candidatos) {
        $j = NormalizarJogo $c
        if ($j) { return $j }
    }
    Write-Host "Não encontrei o jogo automaticamente. Escolha a pasta do Starsector na janela que vai abrir."
    Add-Type -AssemblyName System.Windows.Forms
    $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
    $dlg.Description = "Escolha a pasta do Starsector (a que contém starsector-core)"
    $dlg.ShowNewFolderButton = $false
    if ($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        return NormalizarJogo $dlg.SelectedPath
    }
    return $null
}

function PodeEscrever([string]$pasta) {
    $teste = Join-Path $pasta ("_ptbr_teste_" + [guid]::NewGuid().ToString("N") + ".tmp")
    try {
        [System.IO.File]::WriteAllText($teste, "x")
        Remove-Item -LiteralPath $teste -Force
        return $true
    } catch {
        return $false
    }
}

function AplicarPt([string]$jogo) {
    $originais = @{}
    if (Test-Path -LiteralPath $ArqHashes) {
        $obj = [System.IO.File]::ReadAllText($ArqHashes, $Utf8) | ConvertFrom-Json
        foreach ($p in $obj.PSObject.Properties) { $originais[$p.Name] = $p.Value }
    }
    $anteriores = @{}
    if (Test-Path -LiteralPath $ArqAnteriores) {
        $obj = [System.IO.File]::ReadAllText($ArqAnteriores, $Utf8) | ConvertFrom-Json
        foreach ($p in $obj.PSObject.Properties) { $anteriores[$p.Name] = @($p.Value) }
    }
    $atualizados = New-Object System.Collections.Generic.List[string]
    $novos = New-Object System.Collections.Generic.List[string]
    foreach ($n in (LerNovos)) { $novos.Add($n) }
    $mesclados = New-Object System.Collections.Generic.List[string]
    foreach ($n in (LerManifesto "mesclados")) { $mesclados.Add($n) }
    $recusados = New-Object System.Collections.Generic.List[string]
    $parciais = New-Object System.Collections.Generic.List[string]
    $trocados = 0
    $lista = ArquivosEm $Loc
    $i = 0
    foreach ($rel in $lista) {
        $i++
        if ($i % 50 -eq 0) { Write-Host ("  {0}/{1}" -f $i, $lista.Count) }
        $origem = NoDisco $Loc $rel
        $destino = NoDisco $jogo $rel
        $guardado = NoDisco $Bkp $rel
        if ($mesclados.Contains($rel) -and (Test-Path -LiteralPath $guardado)) {
            # já foi traduzido em parte: refaz a partir da versão do outro mod guardada no backup
            $n = Mesclar $guardado $destino $rel
            $parciais.Add(("{0} ({1} linhas)" -f $rel, $n))
            $trocados++
            continue
        }
        if (Test-Path -LiteralPath $destino) {
            $atual = Hash $destino
            if ($atual -eq (Hash $origem)) {
                # o jogo já tem esta tradução
            } elseif ($atual -eq $originais[$rel]) {
                if (-not (Test-Path -LiteralPath $guardado)) { Copiar $destino $guardado }
            } elseif ((-not (Test-Path -LiteralPath $guardado)) -and $anteriores.ContainsKey($rel) -and ($anteriores[$rel] -contains $atual)) {
                # tradução de uma versão anterior deste kit, e o backup_original dela não existe mais:
                # atualiza direto. Não é "outro mod", então não passa pela mescla.
                $atualizados.Add($rel)
                Copiar $origem $destino
                $trocados++
                continue
            } elseif (-not (Test-Path -LiteralPath $guardado)) {
                # alterado por outro mod: traduz só as linhas que continuam iguais às do original
                $temp = "$destino.ptbr_tmp"
                $n = Mesclar $destino $temp $rel
                if ($n -eq 0) { $recusados.Add($rel); continue }
                Copiar $destino $guardado
                Move-Item -LiteralPath $temp -Destination $destino -Force
                $mesclados.Add($rel)
                $parciais.Add(("{0} ({1} linhas)" -f $rel, $n))
                $trocados++
                continue
            }
        } elseif (-not $novos.Contains($rel)) {
            $novos.Add($rel)
        }
        Copiar $origem $destino
        $trocados++
    }
    GravarManifesto $novos.ToArray() $mesclados.ToArray()
    return @{ Trocados = $trocados; Recusados = $recusados; Parciais = $parciais; Atualizados = $atualizados }
}

function VoltarEn([string]$jogo) {
    $novos = LerNovos
    $mesclados = LerManifesto "mesclados"
    $restaurados = 0
    foreach ($rel in (ArquivosEm $Bkp)) {
        if ($rel -eq "_manifesto.json") { continue }
        Copiar (NoDisco $Bkp $rel) (NoDisco $jogo $rel)
        $restaurados++
    }
    foreach ($rel in $mesclados) {
        # a cópia guardada é a versão do outro mod, já devolvida ao jogo; sem ela, a próxima instalação mescla de novo
        $g = NoDisco $Bkp $rel
        if (Test-Path -LiteralPath $g) { Remove-Item -LiteralPath $g -Force }
    }
    $removidos = 0
    foreach ($rel in $novos) {
        $destino = NoDisco $jogo $rel
        if (Test-Path -LiteralPath $destino) { Remove-Item -LiteralPath $destino -Force; $removidos++ }
    }
    $semOriginal = @(ArquivosEm $Loc | Where-Object {
        -not (Test-Path -LiteralPath (NoDisco $Bkp $_)) -and ($novos -notcontains $_) -and ($mesclados -notcontains $_)
    })
    if (Test-Path -LiteralPath $Manifesto) { Remove-Item -LiteralPath $Manifesto -Force }
    return @{ Restaurados = $restaurados; Removidos = $removidos; SemOriginal = $semOriginal }
}

# ---------------------------------------------------------------- início
Write-Host "Tradução PT-BR do Starsector 0.98.5a-RC4 (kit v$Versao)"
Write-Host ""

if ($Jogo) { $Jogo = NormalizarJogo $Jogo } else { $Jogo = AcharJogo }
if (-not $Jogo) {
    Write-Host "Não encontrei o jogo. Coloque a pasta PTBR_Patch dentro da pasta do Starsector, ao lado de starsector-core, e rode de novo."
    Sair 1
}
$Jogo = (Resolve-Path -LiteralPath $Jogo).ProviderPath
Write-Host "Jogo: $Jogo"

function PodeEscreverTudo([string]$jogo) {
    # o instalador grava no jogo e no backup_original (dentro da pasta do kit); as duas pastas precisam aceitar escrita
    if (-not (PodeEscrever $jogo)) { return $false }
    if (-not (PodeEscrever (Join-Path $jogo "data"))) { return $false }
    if (-not (Test-Path -LiteralPath $Bkp)) {
        try { New-Item -ItemType Directory -Path $Bkp -Force -ErrorAction Stop | Out-Null } catch { return $false }
    }
    return (PodeEscrever $Bkp)
}

function VersaoCompativel([string]$jogo) {
    # compara o jar principal com o original e com o traduzido; outro conteúdo indica outra versão do jogo
    $jar = Join-Path $jogo "starfarer_obf.jar"
    $atual = Hash $jar
    $original = $null
    if (Test-Path -LiteralPath $ArqHashes) {
        $original = ([System.IO.File]::ReadAllText($ArqHashes, $Utf8) | ConvertFrom-Json)."starfarer_obf.jar"
    }
    if (-not $original) { return $true }
    $traduzido = Join-Path $Loc "starfarer_obf.jar"
    if ($atual -eq $original) { return $true }
    if ((Test-Path -LiteralPath $traduzido) -and $atual -eq (Hash $traduzido)) { return $true }
    if (Test-Path -LiteralPath (NoDisco $Bkp "starfarer_obf.jar")) { return $true }
    # jar traduzido por uma versão anterior deste kit
    if (Test-Path -LiteralPath $ArqAnteriores) {
        $ant = ([System.IO.File]::ReadAllText($ArqAnteriores, $Utf8) | ConvertFrom-Json)."starfarer_obf.jar"
        if ($ant -and (@($ant) -contains $atual)) { return $true }
    }
    return $false
}

if ($Acao -eq "pt" -and -not (VersaoCompativel $Jogo)) {
    Write-Host ""
    Write-Host "Este kit é para o Starsector 0.98.5a-RC4, e o seu jogo parece ser de outra versão"
    Write-Host "(o arquivo starfarer_obf.jar não é o da 0.98.5a-RC4)."
    Write-Host "Nada foi alterado. Procure uma versão do kit para a sua versão do jogo."
    Sair 1
}

if (-not (PodeEscreverTudo $Jogo)) {
    Write-Host "O Windows não deixa alterar a pasta do jogo sem permissão de administrador. Pedindo permissão..."
    if ($SemElevar) { Write-Host "(teste: elevação desativada)"; exit 3 }
    $argumentos = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$($MyInvocation.MyCommand.Path)`"",
        "-Acao", $Acao, "-Jogo", "`"$Jogo`"")
    try {
        Start-Process -FilePath "powershell.exe" -ArgumentList $argumentos -Verb RunAs | Out-Null
        exit 0
    } catch {
        Write-Host "A permissão de administrador foi negada. Nada foi alterado."
        Sair 1
    }
}

try {
    if ($Acao -eq "pt") {
        if (-not (Test-Path -LiteralPath $Loc)) { Write-Host "Pasta localization não encontrada."; Sair 1 }
        Write-Host "Aplicando a tradução..."
        $r = AplicarPt $Jogo
        Write-Host ""
        Write-Host ("{0} arquivo(s) traduzido(s) aplicado(s)." -f $r.Trocados)
        Write-Host "Os originais ficam em PTBR_Patch\backup_original. Não apague essa pasta."
        if ($r.Atualizados.Count -gt 0) {
            Write-Host ""
            Write-Host ("{0} arquivo(s) eram de uma versão anterior da tradução e foram atualizados." -f $r.Atualizados.Count)
            Write-Host "Não encontrei o backup_original da versão antiga, então esses arquivos não têm original guardado:"
            Write-Host "o DESINSTALAR.bat não consegue voltá-los ao inglês. Para isso, use a verificação de integridade"
            Write-Host "do jogo (Steam). Na próxima atualização, extraia o zip por cima da pasta PTBR_Patch antiga."
        }
        if ($r.Parciais.Count -gt 0) {
            Write-Host ""
            Write-Host ("{0} arquivo(s) alterado(s) por outro mod foram traduzidos em parte:" -f $r.Parciais.Count)
            $r.Parciais | Select-Object -First 30 | ForEach-Object { Write-Host "    $_" }
            Write-Host "As mudanças do outro mod foram mantidas. Os textos que ele trocou continuam em inglês."
        }
        if ($r.Recusados.Count -gt 0) {
            Write-Host ""
            Write-Host ("{0} arquivo(s) não foram trocados, porque o conteúdo é diferente do original e da tradução:" -f $r.Recusados.Count)
            $r.Recusados | Select-Object -First 30 | ForEach-Object { Write-Host "    $_" }
            Write-Host "Restaure os originais do jogo e rode o instalador de novo."
            Sair 1
        }
        Write-Host "Pronto. Abra o jogo normalmente."
        Sair 0
    } else {
        Write-Host "Voltando ao inglês..."
        $r = VoltarEn $Jogo
        Write-Host ""
        Write-Host ("{0} arquivo(s) original(is) restaurado(s), {1} arquivo(s) novo(s) removido(s)." -f $r.Restaurados, $r.Removidos)
        if ($r.SemOriginal.Count -gt 0) {
            Write-Host ("{0} arquivo(s) não tinham original guardado e continuam como estão:" -f $r.SemOriginal.Count)
            $r.SemOriginal | Select-Object -First 30 | ForEach-Object { Write-Host "    $_" }
        }
        Write-Host "Pronto."
        Sair 0
    }
} catch {
    Write-Host ""
    Write-Host "Erro: $($_.Exception.Message)"
    if ($_.Exception -is [System.UnauthorizedAccessException]) {
        Write-Host "O Windows negou acesso a um arquivo. Clique com o botão direito em INSTALAR.bat e escolha"
        Write-Host "'Executar como administrador'. Se o jogo ou o launcher estiverem abertos, feche-os antes."
    } elseif ($_.Exception -is [System.IO.IOException]) {
        Write-Host "Um arquivo está em uso. Feche o jogo e o launcher e rode de novo."
    }
    Write-Host "Os arquivos já trocados têm o original guardado em backup_original; rodar de novo é seguro."
    Sair 1
}
