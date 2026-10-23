"""Build the small OpenSSL arithmetic helper without downloading dependencies."""
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
compiler = shutil.which("clang") or shutil.which("cc")
if not compiler:
    sys.exit("Install a C compiler to enable the native arithmetic evaluator.")
target = root / "build" / "aggregate"
target.parent.mkdir(exist_ok=True)
args = [compiler,"-O2","-Wall","-Wextra","-Werror",str(root/"src"/"aggregate.c"),"-o",str(target)]
brew = Path("/opt/homebrew/opt/openssl@3")
if brew.exists():
    args += ["-I"+str(brew/"include"),"-L"+str(brew/"lib"),"-Wl,-rpath,"+str(brew/"lib")]
args += ["-lcrypto"]
subprocess.run(args,check=True)
print("Built native Paillier evaluator: build/aggregate")
