# start_friday.py
import sys
import os

try:
    # Attempt to import the ProcessManager
    from process_manager import ProcessManager
except ImportError:
    print("⚠️ Process manager not found. Please make sure process_manager.py exists.")
    sys.exit(1)

def main():
    print("🤖 Starting Friday AI with process management...")
    
    # Create and start the process manager
    manager = ProcessManager()
    result = manager.start()
    
    if not result:
        print("⚠️ Friday AI failed to start. Check logs for details.")
    else:
        print("👋 Friday AI has been shut down")

if __name__ == "__main__":
    main()