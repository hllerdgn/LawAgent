$ErrorActionPreference = 'Stop'
Write-Host "Aktif sanal ortama geciliyor..."
& ".\.venv\Scripts\Activate.ps1"

Write-Host "Generator API baslatiliyor..."
Start-Process -NoNewWindow -FilePath "uvicorn" -ArgumentList "main:app --host 0.0.0.0 --port 8000"

Write-Host "Streamlit UI baslatiliyor..."
Start-Process -NoNewWindow -FilePath "streamlit" -ArgumentList "run app.py"

Write-Host "Backend ve Frontend servisi baslatildi! Uygulama tarayicida aciliyor."
