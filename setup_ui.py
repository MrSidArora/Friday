# setup_ui.py
import os
import subprocess
import sys
import platform
import shutil

def setup_ui():
    print("🚀 Setting up Friday AI User Interface")
    
    # Navigate to the electron_app directory
    ui_dir = os.path.join("ui", "electron_app")
    
    # Create directories if they don't exist
    os.makedirs(ui_dir, exist_ok=True)
    os.makedirs(os.path.join(ui_dir, "styles"), exist_ok=True)
    os.makedirs(os.path.join(ui_dir, "assets", "images"), exist_ok=True)
    os.makedirs(os.path.join(ui_dir, "assets", "icons"), exist_ok=True)
    
    # Check if Node.js is installed
    try:
        result = subprocess.run(["node", "--version"], check=True, capture_output=True, text=True)
        node_version = result.stdout.strip()
        print(f"✅ Node.js detected (Version: {node_version})")
    except (subprocess.SubprocessError, FileNotFoundError):
        print("❌ Node.js not found. Please install Node.js from https://nodejs.org/")
        sys.exit(1)
    
    # Check if npm is installed - in Windows use 'where' command instead of 'which'
    npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
    
    # Check if npm is available
    try:
        result = subprocess.run([npm_cmd, "--version"], check=True, capture_output=True, text=True)
        npm_version = result.stdout.strip()
        print(f"✅ npm detected (Version: {npm_version})")
    except (subprocess.SubprocessError, FileNotFoundError):
        print("❌ npm not found. Please check your Node.js installation as npm should be included.")
        sys.exit(1)
    
    # Navigate to UI directory and install dependencies
    print("📦 Installing Electron dependencies...")
    
    # Save current directory
    current_dir = os.getcwd()
    
    # Change to UI directory
    ui_full_path = os.path.join(current_dir, ui_dir)
    os.chdir(ui_full_path)
    
    try:
        subprocess.run([npm_cmd, "install"], check=True)
        print("✅ Dependencies installed successfully")
    except subprocess.SubprocessError as e:
        print(f"❌ Failed to install dependencies: {str(e)}")
        # Change back to original directory
        os.chdir(current_dir)
        sys.exit(1)
    
    # Change back to original directory
    os.chdir(current_dir)
    
    # Install Python WebSocket server dependencies
    print("📦 Installing Python WebSocket dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "websockets"], check=True)
        print("✅ WebSockets library installed successfully")
    except subprocess.SubprocessError as e:
        print(f"❌ Failed to install WebSockets: {str(e)}")
        sys.exit(1)
    
    print("\n🎉 Friday UI setup complete!")
    print("\nTo start the UI:")
    print("1. Navigate to friday/ui/electron_app")
    print(f"2. Run '{npm_cmd} start'")
    print("\nTo enable development mode:")
    print("1. Navigate to friday/ui/electron_app")
    print(f"2. Run '{npm_cmd} run dev'")

if __name__ == "__main__":
    setup_ui()