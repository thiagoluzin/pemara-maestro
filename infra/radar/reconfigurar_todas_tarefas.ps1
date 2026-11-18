# reconfigurar_todas_tarefas.ps1
# Script para registrar Pemara_Radar e reconfigurar as outras tarefas para rodarem sob admin_remoto com LogonType S4U

Write-Host "============================================================"
Write-Host "  RECONFIGURADOR DE TAREFAS PEMARA - TECH"
Write-Host "============================================================"
Write-Host ""

# 1. Registrar Pemara_Radar
Write-Host "[1/4] Registrando Pemara_Radar..."
& "E:\Pemara\radar\register_task.ps1"
if ($LASTEXITCODE -eq 0 -or $?) {
    Write-Host "  [OK] Pemara_Radar registrada com sucesso."
} else {
    Write-Warning "  [FALHA] Não foi possível registrar Pemara_Radar automaticamente."
}

# 2. Reconfigurar e corrigir tarefas existentes
$tasks = @("PemaraBackup", "PemaraComfyUI", "PemaraLojaAutoStart")
$principal = New-ScheduledTaskPrincipal -UserId "admin_remoto" -LogonType S4U -RunLevel Highest

foreach ($taskName in $tasks) {
    Write-Host ""
    Write-Host "[*] Processando tarefa: $taskName..."
    try {
        $task = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
        
        # Obter ações originais
        $action = $task.Actions
        
        # Corrigir o caminho do ComfyUI se for a tarefa PemaraComfyUI
        if ($taskName -eq "PemaraComfyUI") {
            Write-Host "  Corrigindo caminhos da tarefa PemaraComfyUI..."
            $oldPath = "E:\PROJETOS\TESTES\CONVERSOR_EDITOR\pemara_universal_v4.0_1\pemara\ferramentas\ComfyUI\main.py"
            $newPath = "E:\Pemara\maestro\pemara\ferramentas\ComfyUI\main.py"
            
            # Se a ação usar o caminho antigo, atualiza
            if ($action.Arguments -like "*CONVERSOR_EDITOR*") {
                $args = $action.Arguments -replace [regex]::Escape($oldPath), $newPath
                $action = New-ScheduledTaskAction -Execute $action.Execute -Argument $args -WorkingDirectory "E:\Pemara\maestro\pemara\ferramentas\ComfyUI"
                Write-Host "  [OK] Caminho do ComfyUI atualizado na tarefa."
            }
        }
        
        # Re-registrar a tarefa com o novo principal S4U
        Register-ScheduledTask -TaskName $task.TaskName -Action $action -Trigger $task.Triggers -Settings $task.Settings -Principal $principal -Force | Out-Null
        Write-Host "  [OK] Tarefa $taskName reconfigurada com sucesso para LogonType S4U."
    } catch {
        Write-Warning "  [AVISO] Não foi possível reconfigurar a tarefa $taskName. Detalhes: $_"
    }
}

Write-Host ""
Write-Host "[3/4] Iniciando a tarefa Pemara_Radar..."
try {
    Start-ScheduledTask -TaskName "Pemara_Radar"
    Write-Host "  [OK] Pemara_Radar iniciada no Task Scheduler."
} catch {
    Write-Warning "  [FALHA] Não foi possível iniciar a tarefa Pemara_Radar."
}

Write-Host ""
Write-Host "============================================================"
Write-Host "  RECONFIGURAÇÃO CONCLUÍDA COM SUCESSO!"
Write-Host "============================================================"
