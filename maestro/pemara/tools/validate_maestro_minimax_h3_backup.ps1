[CmdletBinding()]
param([string]$PackageRoot = $PSScriptRoot)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $PackageRoot).Path
$manifestPath = Join-Path $root 'MANIFEST_SHA256.csv'
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw 'MANIFEST_SHA256.csv ausente.' }
$manifest = Import-Csv -LiteralPath $manifestPath
$failures = [System.Collections.Generic.List[string]]::new()
foreach ($item in $manifest) {
    $path = Join-Path $root $item.RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        $failures.Add("AUSENTE $($item.RelativePath)")
        continue
    }
    $file = Get-Item -LiteralPath $path
    if ($file.Length -ne [int64]$item.Bytes) {
        $failures.Add("TAMANHO $($item.RelativePath)")
        continue
    }
    $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
    if ($hash -ne $item.SHA256) { $failures.Add("HASH $($item.RelativePath)") }
}
if (Get-ChildItem -LiteralPath (Join-Path $root 'payload') -Recurse -Force -File | Where-Object { $_.Name -eq '.env' }) {
    $failures.Add('SEGREDO arquivo .env encontrado no payload')
}
$installerRequired = @(
    'INSTALAR_MODELOS\INSTALAR_TUDO_MODELOS.bat',
    'INSTALAR_MODELOS\01_INSTALAR_H3.bat',
    'INSTALAR_MODELOS\02_INSTALAR_QWEN_H3.bat',
    'INSTALAR_MODELOS\03_INSTALAR_RIFE_FHD60.bat',
    'INSTALAR_MODELOS\04_INSTALAR_FOLEY_XXL.bat',
    'INSTALAR_MODELOS\VERIFICAR_MODELOS.bat',
    'INSTALAR_MODELOS\install_models.py',
    'INSTALAR_MODELOS\models.lock.json'
)
foreach ($relative in $installerRequired) {
    if (-not (Test-Path -LiteralPath (Join-Path $root $relative) -PathType Leaf)) {
        $failures.Add("INSTALADOR AUSENTE $relative")
    }
}
$weightExtensions = @('.safetensors', '.ckpt', '.pt', '.pth', '.onnx', '.gguf', '.engine', '.tflite', '.mlmodel', '.param')
$unexpectedWeights = @(Get-ChildItem -LiteralPath (Join-Path $root 'payload') -Recurse -Force -File | Where-Object { $_.Extension.ToLowerInvariant() -in $weightExtensions })
if ($unexpectedWeights.Count) {
    $failures.Add("PESO DE MODELO encontrado no payload: $($unexpectedWeights[0].FullName)")
}
if ($failures.Count) { throw ("Backup invalido:`n" + ($failures -join "`n")) }
Write-Output "PASS backup integro: $($manifest.Count) arquivos."
