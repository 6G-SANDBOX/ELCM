$port = if ($null -eq $args[0]) { "5001" } else { $args[0] }

Write-Host "Starting ELCM on port $port"

& ./venv/Scripts/activate.ps1
& waitress-serve --threads=1 --listen=*:$port Scheduler:app
& deactivate