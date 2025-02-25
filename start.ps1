$port = if ($null -eq $args[0]) { "5001" } else { $args[0] }

Write-Host "Starting ELCM on port $port"

& ./venv/Scripts/activate.ps1
& flask run --host 0.0.0.0 --port $port
& deactivate