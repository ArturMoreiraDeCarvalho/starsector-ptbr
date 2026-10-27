# Instalador da tradução PT-BR do Starsector 0.98a-RC8.
# Use INSTALAR.bat e DESINSTALAR.bat; este arquivo faz o trabalho.
# Mesma lógica e mesmo backup do _swapLangFile.py: os dois podem ser usados no mesmo jogo.
param(
    [Parameter(Mandatory = $true)][ValidateSet("pt", "en")][string]$Acao,
    [string]$Jogo,
    [switch]$SemPausa
)

$ErrorActionPreference = "Stop"
$Kit = Split-Path -Parent $MyInvocation.MyCommand.Path
$Loc = Join-Path $Kit "localization"
$Bkp = Join-Path $Kit "backup_original"
$Manifesto = Join-Path $Bkp "_manifesto.json"
$ArqHashes = Join-Path $Kit "hashes_originais.json"
$Utf8 = New-Object System.Text.UTF8Encoding($false)

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

function LerNovos {
    if (-not (Test-Path -LiteralPath $Manifesto)) { return @() }
    $dados = [System.IO.File]::ReadAllText($Manifesto, $Utf8) | ConvertFrom-Json
    @($dados.novos | Where-Object { $_ })
}

function GravarNovos([string[]]$novos) {
    if (-not (Test-Path -LiteralPath $Bkp)) { New-Item -ItemType Directory -Path $Bkp -Force | Out-Null }
    $itens = @($novos | ForEach-Object { '"' + ($_ -replace '\\', '\\' -replace '"', '\"') + '"' })
    $json = '{"novos": [' + ($itens -join ", ") + ']}'
    [System.IO.File]::WriteAllText($Manifesto, $json, $Utf8)
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
    $novos = New-Object System.Collections.Generic.List[string]
    foreach ($n in (LerNovos)) { $novos.Add($n) }
    $recusados = New-Object System.Collections.Generic.List[string]
    $trocados = 0
    $lista = ArquivosEm $Loc
    $i = 0
    foreach ($rel in $lista) {
        $i++
        if ($i % 50 -eq 0) { Write-Host ("  {0}/{1}" -f $i, $lista.Count) }
        $origem = NoDisco $Loc $rel
        $destino = NoDisco $jogo $rel
        $guardado = NoDisco $Bkp $rel
        if (Test-Path -LiteralPath $destino) {
            $atual = Hash $destino
            if ($atual -eq (Hash $origem)) {
                # o jogo já tem esta tradução
            } elseif ($atual -eq $originais[$rel]) {
                if (-not (Test-Path -LiteralPath $guardado)) { Copiar $destino $guardado }
            } elseif (-not (Test-Path -LiteralPath $guardado)) {
                $recusados.Add($rel)
                continue
            }
        } elseif (-not $novos.Contains($rel)) {
            $novos.Add($rel)
        }
        Copiar $origem $destino
        $trocados++
    }
    GravarNovos $novos.ToArray()
    return @{ Trocados = $trocados; Recusados = $recusados }
}

function VoltarEn([string]$jogo) {
    $novos = LerNovos
    $restaurados = 0
    foreach ($rel in (ArquivosEm $Bkp)) {
        if ($rel -eq "_manifesto.json") { continue }
        Copiar (NoDisco $Bkp $rel) (NoDisco $jogo $rel)
        $restaurados++
    }
    $removidos = 0
    foreach ($rel in $novos) {
        $destino = NoDisco $jogo $rel
        if (Test-Path -LiteralPath $destino) { Remove-Item -LiteralPath $destino -Force; $removidos++ }
    }
    $semOriginal = @(ArquivosEm $Loc | Where-Object {
        -not (Test-Path -LiteralPath (NoDisco $Bkp $_)) -and ($novos -notcontains $_)
    })
    if (Test-Path -LiteralPath $Manifesto) { Remove-Item -LiteralPath $Manifesto -Force }
    return @{ Restaurados = $restaurados; Removidos = $removidos; SemOriginal = $semOriginal }
}

# ---------------------------------------------------------------- início
Write-Host "Tradução PT-BR do Starsector 0.98a-RC8"
Write-Host ""

if ($Jogo) { $Jogo = NormalizarJogo $Jogo } else { $Jogo = AcharJogo }
if (-not $Jogo) {
    Write-Host "Não encontrei o jogo. Coloque a pasta PTBR_Patch dentro da pasta do Starsector, ao lado de starsector-core, e rode de novo."
    Sair 1
}
$Jogo = (Resolve-Path -LiteralPath $Jogo).ProviderPath
Write-Host "Jogo: $Jogo"

if (-not (PodeEscrever $Jogo)) {
    Write-Host "Sem permissão para alterar a pasta do jogo. Pedindo permissão de administrador..."
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
    Write-Host "Se o jogo estiver aberto, feche-o e rode de novo."
    Sair 1
}
