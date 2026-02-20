from app import app
import webbrowser
import threading
import time
import sys

def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:5000")

def main():
    if getattr(sys, 'frozen', False):
        # We are running in a bundle
        # Briefcase might not set sys.frozen the same way PyInstaller does, 
        # but Toga apps usually have their own entry point.
        pass

    # Start browser in a separate thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run Flask app
    # Host 127.0.0.1 is safer for desktop app than 0.0.0.0
    app.run(host="127.0.0.1", port=5000, debug=False)

if __name__ == "__main__":
    main()
