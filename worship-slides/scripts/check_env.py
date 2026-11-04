"""Check what the worship-slides scripts need. Exit code 0 = ready to build."""
import importlib.util, shutil, sys
need = {"pptx": "python-pptx", "lxml": "lxml", "yaml": "PyYAML", "pdfplumber": "pdfplumber", "PIL": "Pillow"}
missing = [pkg for mod, pkg in need.items() if importlib.util.find_spec(mod) is None]
print("python  ", sys.version.split()[0])
print("packages", "ok" if not missing else "MISSING: " + " ".join(missing))
office = shutil.which("soffice") or shutil.which("libreoffice")
print("previews", f"LibreOffice at {office}" if office else "no LibreOffice (build works, previews skipped)")
print("fonts    the presenting PC needs KaiTi + Cambria (Windows/Office have both)")
sys.exit(1 if missing else 0)
