import sys
from cx_Freeze import setup, Executable
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "src", "shopease"))

# Dependencies are automatically detected, but it might need fine tuning.
# "packages": ["os"] is used as example
build_exe_options = {
    "packages": [
        "os", "flask", "flask_sqlalchemy", "sqlalchemy", 
        "pandas", "numpy", "fpdf", "qrcode", "PIL"
    ],
    "include_files": [
        ("src/shopease/templates", "templates"),
        ("src/shopease/static", "static"),
        ("src/shopease/customers.xlsx", "customers.xlsx"),
        ("instance/shop.db", "shop.db"),
    ],
    "includes": ["src.shopease.generate_daily_sales"], # Force include dynamic import
    "excludes": ["tkinter"],
}

# base="Win32GUI" should be used only for Windows GUI app
base = None
if sys.platform == "win32":
    # base = "Win32GUI" # Use this to hide the console
    base = None # Use this to see the console for debugging

setup(
    name="ShopEase",
    version="1.0",
    description="Smart Shop Manager",
    options={"build_exe": build_exe_options},
    executables=[Executable("src/shopease/app.py", base=base, target_name="ShopEase.exe")],
)
