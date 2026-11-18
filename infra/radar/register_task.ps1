$action = New-ScheduledTaskAction -Execute 'C:\Program Files\Python311\python.exe' -Argument 'E:\Pemara\radar\radar_monitor.py' -WorkingDirectory 'E:\Pemara\radar'
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 365) -Compatibility Win8 -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId 'admin_remoto' -LogonType S4U -RunLevel Highest
Register-ScheduledTask -TaskName 'Pemara_Radar' -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Agente de monitoramento e recuperacao Pemara Tech' -Force
