import subprocess
import time

def main():
    print("==========================================")
    print("FiscalFlow Stop Utility")
    print("==========================================")

    print("Stopping any running process on port 8000...")
    cmd = "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
    subprocess.run(["powershell", "-Command", cmd], capture_output=True)

    print("Server stopped successfully.")
    time.sleep(1.5)

if __name__ == "__main__":
    main()
