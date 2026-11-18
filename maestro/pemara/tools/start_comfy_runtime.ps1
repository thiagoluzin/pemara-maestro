[CmdletBinding()]
param(
    [int]$Port = 8188,
    [string]$RuntimeRoot = 'D:\PemaraRuntimes\ComfyUI-v0.40.0-pemara',
    [string]$Python = 'D:\PemaraRuntimes\comfyui-v0400-py311\Scripts\python.exe',
    [string]$IoRoot = 'E:\Pemara\maestro\pemara\ferramentas\ComfyUI',
    [string]$UserDirectory = 'D:\PemaraRuntimes\state\ComfyUI-v0.40.0-pemara\user',
    [string]$ExpectedComfy = '0.41.0',
    [string]$ExpectedTorch = '2.14.0+cu130',
    [int]$TimeoutSeconds = 120
)

$ErrorActionPreference = 'Stop'
if ($Port -ne 8188 -or $RuntimeRoot -ne 'D:\PemaraRuntimes\ComfyUI-v0.40.0-pemara' -or
    $Python -ne 'D:\PemaraRuntimes\comfyui-v0400-py311\Scripts\python.exe') {
    throw 'O servico central tem contrato fixo; use uma instalacao de laboratorio explicita.'
}
& 'E:\Pemara\maestro\pemara\ferramentas\comfy_mcp_runtime\Scripts\python.exe' `
    'E:\Pemara\maestro\pemara\tools\comfy_lifecycle.py' start --automatic
if ($LASTEXITCODE -ne 0) { throw 'Falha no controlador central do ComfyUI.' }
