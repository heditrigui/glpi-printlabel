# Windows: start the glpi-label agent at logon (run in PowerShell as the user)
$exe = (Get-Command glpi-label.exe).Source
$action = New-ScheduledTaskAction -Execute $exe -Argument "serve"
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit 0 -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName "glpi-label" -Action $action -Trigger $trigger -Settings $settings -Force
Start-ScheduledTask -TaskName "glpi-label"
