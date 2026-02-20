from cx_Freeze import setup, Executable

setup(
    name="HelloCX",
    version="0.1",
    description="Test",
    executables=[Executable("hello_cx.py")],
)
