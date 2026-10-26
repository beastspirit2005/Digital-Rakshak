$dest = "backend\wheels\torch-2.6.0+cu124-cp310-cp310-win_amd64.whl"
$url = "https://download-r2.pytorch.org/whl/cu124/torch-2.6.0%2Bcu124-cp310-cp310-win_amd64.whl"
$targetSize = 2532341467

Write-Host "Starting / Resuming resilient PyTorch CUDA download..."

while ($true) {
    if (Test-Path $dest) {
        $curSize = (Get-Item $dest).Length
        if ($curSize -ge $targetSize) {
            Write-Host "Download Complete! Size: $curSize bytes"
            break
        }
        Write-Host "Current Progress: $([math]::Round($curSize / 1MB, 1)) MB / $([math]::Round($targetSize / 1MB, 1)) MB ($([math]::Round(($curSize / $targetSize) * 100, 1))%)"
    }

    # Run curl with auto-resume
    curl.exe -L -C - --retry 10 --retry-delay 2 -o $dest $url

    if (Test-Path $dest) {
        $curSize = (Get-Item $dest).Length
        if ($curSize -ge $targetSize) {
            Write-Host "PyTorch CUDA Wheel fully downloaded ($curSize bytes)!"
            break
        }
    }
    Write-Host "Retrying in 2 seconds..."
    Start-Sleep -Seconds 2
}

Write-Host "Installing PyTorch CUDA wheel..."
backend\venv_clean\Scripts\pip.exe install $dest --force-reinstall --no-deps
Write-Host "Verifying CUDA availability..."
backend\venv_clean\Scripts\python.exe -c "import torch; print('CUDA AVAILABLE:', torch.cuda.is_available(), 'DEVICE:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE')"
