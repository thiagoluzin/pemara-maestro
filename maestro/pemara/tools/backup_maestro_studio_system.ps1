[CmdletBinding()]
param(
    [string]$SourceRoot = 'E:\Pemara\maestro',
    [string]$DestinationRoot = 'G:\Pemara_Backups'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$source = (Resolve-Path -LiteralPath $SourceRoot).Path.TrimEnd('\')
$destinationBase = (Resolve-Path -LiteralPath $DestinationRoot).Path.TrimEnd('\')
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupName = "Maestro_Studio_Sistema_$stamp"
$package = Join-Path $destinationBase $backupName
$payload = Join-Path $package 'payload'
$zipPath = "$package.zip"
$sidecarPath = "$zipPath.sha256"

if (-not (Test-Path -LiteralPath (Join-Path $source '.git') -PathType Container)) {
    throw "Repositorio Maestro nao encontrado em $source"
}
if ($package -eq $destinationBase -or -not $package.StartsWith("$destinationBase\", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Destino de backup inseguro: $package"
}
if ((Test-Path -LiteralPath $package) -or (Test-Path -LiteralPath $zipPath)) {
    throw "O destino novo ja existe: $package"
}

$excludedSegments = [regex]'^(\.git|\.venv|venv[^\\/]*|node_modules|__pycache__|\.pytest_cache|models?|checkpoints?|ckpts?|weights|loras?|lora_videos|input|output|temp|PRONTOS)$'
$excludedExtensions = [regex]'\.(pyc|pyo|log|tmp|safetensors|ckpt|pt|pth|onnx|gguf|engine|tflite|mlmodel|param|mp4|mov|mkv|webm|wav|flac|mp3|zip|7z|rar)$'
$privateExtensions = [regex]'\.(pem|key|p12|pfx)$'

function Test-BackupCandidate {
    param([Parameter(Mandatory)][string]$RelativePath)

    $normalized = $RelativePath.Replace('\', '/')
    foreach ($segment in ($normalized -split '/')) {
        if ($excludedSegments.IsMatch($segment)) { return $false }
    }
    if ($normalized -match '(^|/)ferramentas/video_global_engine/projetos(/|$)') { return $false }
    if ($normalized -match '(^|/)\.cloudflared(/|$)') { return $false }
    if ($normalized -match '(^|/)\.env$') { return $false }
    if ($excludedExtensions.IsMatch($normalized)) { return $false }
    if ($privateExtensions.IsMatch($normalized)) { return $false }
    return $true
}

New-Item -ItemType Directory -Path $payload -Force | Out-Null

$gitPaths = @(& git -C $source ls-files -co --exclude-standard)
if ($LASTEXITCODE -ne 0 -or $gitPaths.Count -eq 0) {
    throw 'Nao foi possivel inventariar os arquivos visiveis ao Git.'
}

$copied = [System.Collections.Generic.List[object]]::new()
foreach ($relativePath in $gitPaths) {
    if (-not (Test-BackupCandidate -RelativePath $relativePath)) { continue }
    $sourceFile = Join-Path $source $relativePath
    if (-not (Test-Path -LiteralPath $sourceFile -PathType Leaf)) { continue }

    $destinationFile = Join-Path $payload $relativePath
    $destinationDirectory = Split-Path -Parent $destinationFile
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
    Copy-Item -LiteralPath $sourceFile -Destination $destinationFile

    $sourceItem = Get-Item -LiteralPath $sourceFile
    $sourceHash = (Get-FileHash -LiteralPath $sourceFile -Algorithm SHA256).Hash
    $destinationHash = (Get-FileHash -LiteralPath $destinationFile -Algorithm SHA256).Hash
    $copied.Add([pscustomobject]@{
        RelativePath = $relativePath.Replace('\', '/')
        Bytes = $sourceItem.Length
        SHA256 = $destinationHash
        SourceMatches = ($sourceHash -eq $destinationHash)
    })
}

$mismatches = @($copied | Where-Object { -not $_.SourceMatches })
if ($mismatches.Count -gt 0) {
    throw "Falha de integridade entre origem e copia: $($mismatches.Count) arquivo(s)."
}

$branch = (& git -C $source branch --show-current).Trim()
$head = (& git -C $source rev-parse HEAD).Trim()
& git -C $source status --short --branch | Set-Content -LiteralPath (Join-Path $package 'GIT_STATUS.txt') -Encoding utf8
& git -C $source diff --binary | Set-Content -LiteralPath (Join-Path $package 'GIT_DIFF.patch') -Encoding utf8

$validator = @'
[CmdletBinding()]
param([string]$BackupRoot = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
$manifestPath = Join-Path $BackupRoot 'MANIFEST_SHA256.csv'
$manifest = Import-Csv -LiteralPath $manifestPath
$failures = foreach ($row in $manifest) {
    $file = Join-Path $BackupRoot $row.RelativePath
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        [pscustomobject]@{ RelativePath = $row.RelativePath; Problem = 'missing' }
        continue
    }
    $item = Get-Item -LiteralPath $file
    $hash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash
    if ($item.Length -ne [int64]$row.Bytes -or $hash -ne $row.SHA256) {
        [pscustomobject]@{ RelativePath = $row.RelativePath; Problem = 'size_or_hash' }
    }
}
$failures = @($failures)
if ($failures.Count -gt 0) {
    $failures | Format-Table -AutoSize
    throw "Backup invalido: $($failures.Count) divergencia(s)."
}
Write-Output "PASS: $($manifest.Count) arquivos conferidos por tamanho e SHA-256."
'@
$validator | Set-Content -LiteralPath (Join-Path $package 'VALIDAR_BACKUP.ps1') -Encoding utf8

$readme = @"
# Copia do sistema Maestro/Studio

Criada em $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss zzz') a partir de ``$source``.

## Escopo

- Codigo, configuracoes publicas, scripts, testes, documentacao e assets essenciais visiveis ao Git.
- Branch de referencia: ``$branch``.
- Commit de referencia: ``$head``.
- Alteracoes locais ainda nao commitadas foram copiadas no estado atual dos arquivos.
- O historico interno ``.git`` nao faz parte deste pacote.

## Exclusoes intencionais

- ``.env``, chaves privadas, credenciais de tunel e certificados privados;
- bancos, dados operacionais, entradas, saidas e logs;
- modelos, checkpoints, ambientes Python, ``node_modules`` e caches;
- takes, renders, projetos de producao, datasets e arquivos de treinamento;
- arquivos compactados e backups anteriores.

## Verificacao

- Execute ``VALIDAR_BACKUP.ps1`` dentro da pasta extraida.
- ``MANIFEST_SHA256.csv`` registra tamanho e SHA-256 de todos os arquivos do pacote, exceto o proprio manifesto.
- A criacao comparou origem e copia com zero divergencias.

## Restauracao segura

1. Valide primeiro o SHA-256 do ZIP usando o arquivo ``.zip.sha256``.
2. Extraia em uma pasta vazia e execute ``VALIDAR_BACKUP.ps1``.
3. Nao sobrescreva o Maestro ativo sem parar apenas os servicos exatos e criar outro snapshot do estado corrente.
4. Reinstale dependencias e restaure segredos somente de uma fonte privada autorizada.
5. Valide Maestro, Studio e testes antes de promover a copia restaurada.
"@
$readme | Set-Content -LiteralPath (Join-Path $package 'LEIA-ME_RESTAURACAO.md') -Encoding utf8

$payloadBytes = ($copied | Measure-Object -Property Bytes -Sum).Sum
$metadata = [ordered]@{
    schemaVersion = 2
    createdAt = (Get-Date).ToString('o')
    source = $source
    destination = $package
    scope = 'Git-visible Maestro system source and public configuration'
    branch = $branch
    head = $head
    payloadFiles = $copied.Count
    payloadBytes = $payloadBytes
    sourceDestinationHashMismatches = $mismatches.Count
    secretsIncluded = $false
    projectsIncluded = $false
    modelsIncluded = $false
    generatedMediaIncluded = $false
}
$metadata | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $package 'SNAPSHOT_METADATA.json') -Encoding utf8

$packageFiles = @(Get-ChildItem -LiteralPath $package -Recurse -File)
$manifest = foreach ($file in $packageFiles) {
    [pscustomobject]@{
        RelativePath = $file.FullName.Substring($package.Length + 1).Replace('\', '/')
        Bytes = $file.Length
        SHA256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
    }
}
$manifest | Export-Csv -LiteralPath (Join-Path $package 'MANIFEST_SHA256.csv') -NoTypeInformation -Encoding utf8

& (Join-Path $package 'VALIDAR_BACKUP.ps1') -BackupRoot $package | Out-Null

Compress-Archive -LiteralPath $package -DestinationPath $zipPath -CompressionLevel Optimal
$zipHash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash
"$zipHash *$([IO.Path]::GetFileName($zipPath))" | Set-Content -LiteralPath $sidecarPath -Encoding ascii

Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
try {
    $prefix = "$backupName/"
    $zipFailures = [System.Collections.Generic.List[string]]::new()
    foreach ($row in $manifest) {
        $entryName = ($prefix + $row.RelativePath).Replace('\', '/')
        $entry = $archive.Entries | Where-Object { $_.FullName -eq $entryName } | Select-Object -First 1
        if ($null -eq $entry) {
            $zipFailures.Add("missing:$entryName")
            continue
        }
        $stream = $entry.Open()
        try {
            $sha = [System.Security.Cryptography.SHA256]::Create()
            try { $entryHash = [Convert]::ToHexString($sha.ComputeHash($stream)) }
            finally { $sha.Dispose() }
        }
        finally { $stream.Dispose() }
        if ($entry.Length -ne [int64]$row.Bytes -or $entryHash -ne $row.SHA256) {
            $zipFailures.Add("size_or_hash:$entryName")
        }
    }
    if ($zipFailures.Count -gt 0) {
        throw "ZIP invalido: $($zipFailures.Count) divergencia(s)."
    }
}
finally { $archive.Dispose() }

$result = [ordered]@{
    backupName = $backupName
    folder = $package
    zip = $zipPath
    zipSidecar = $sidecarPath
    payloadFiles = $copied.Count
    manifestFiles = $manifest.Count
    payloadBytes = $payloadBytes
    zipBytes = (Get-Item -LiteralPath $zipPath).Length
    zipSHA256 = $zipHash
    sourceDestinationHashMismatches = $mismatches.Count
    zipHashMismatches = 0
}
$result | ConvertTo-Json -Depth 4
