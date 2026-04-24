param([string]$PiHost = "raspberrypi.local", [string]$PiUser = "pi")

Write-Host "Deploying to $PiUser@$PiHost..." -ForegroundColor Cyan

ssh "$PiUser@$PiHost" "mkdir -p ~/mariner/pi_scripts"
scp -r .\pi_scripts\* "$PiUser@$PiHost`:~/mariner/pi_scripts/"
ssh "$PiUser@$PiHost" "chmod +x ~/mariner/pi_scripts/*.sh"

Write-Host "Done! Run: ssh $PiUser@$PiHost 'cd ~/mariner/pi_scripts && ./start_all_services.sh'" -ForegroundColor Green
