"""Run a command under an address-space limit (RLIMIT_AS, as tools/envmatrix.py does) and
summarise its output: exit code, output size, first bytes. Usage: 04-aslimit.py MB cmd..."""
import os, resource, subprocess, sys
mb = int(sys.argv[1])
def limit():
    if mb:
        resource.setrlimit(resource.RLIMIT_AS, (mb * 2**20, mb * 2**20))
p = subprocess.run(sys.argv[2:], capture_output=True, preexec_fn=limit, env=dict(os.environ, PYTHONPATH="src"))
print(f"RLIMIT_AS {mb or 'unlimited'} MB: exit {p.returncode}, {len(p.stdout)} bytes of output")
print("  first 160 bytes:", p.stdout[:160])
print("  last 60 bytes:  ", p.stdout[-60:])
