import os
import subprocess
import webbrowser
import time

def main():
    print("==========================================")
    print("FiscalFlow Startup Utility")
    print("==========================================")

    # 1. Stop any existing process on port 8000
    print("[1/3] Stopping any existing process on port 8000...")
    cmd = "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
    subprocess.run(["powershell", "-Command", cmd], capture_output=True)
    time.sleep(0.5)

    # 2. Open browser tab
    print("[2/3] Launching FiscalFlow browser tab...")
    webbrowser.open("http://127.0.0.1:8000")

    # 3. Start backend server
    print("[3/3] Starting FiscalFlow backend & frontend server...")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(current_dir, "backend")
    venv_python = os.path.join(backend_dir, ".venv", "Scripts", "python.exe")

    if not os.path.exists(venv_python):
        print("Warning: Local virtual environment (.venv) python not found. Falling back to system python.")
        venv_python = "python"

    try:
        subprocess.run(
            [venv_python, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"],
            cwd=backend_dir
        )
    except KeyboardInterrupt:
        print("\nServer stopped by user.")

if __name__ == "__main__":
    main()
