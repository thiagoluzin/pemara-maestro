param(
    [string]$Reason = "ordem do usuario: treino da intro desde 13:00 ate segunda ordem"
)

$ErrorActionPreference = "Stop"
$message = "Treinamento Wan foi removido por ordem do proprietario. Este iniciador esta aposentado. Motivo recebido: $Reason"
Write-Error $message
exit 32
