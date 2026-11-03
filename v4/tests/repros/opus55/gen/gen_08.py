"""Write 08-rename-a.rl (name f) and 08-rename-b.rl (the same program with f renamed one-to-one),
padded with a comment so that a is just under the 1 000 000-byte program bound."""
H = "d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8"  # participants.tsv
def prog(name, pad):
    body = f"file {name} = sha256:{H}\nclaim rows(tsv({name})) is 108\n"
    return body + "#" + "x" * pad + "\n"
base = len(prog("f", 0).encode())
pad = 1_000_000 - base - 10
a = prog("f", pad); b = prog("participants_file", pad)
open("findings/08-rename-a.rl", "w", newline="\n").write(a)
open("findings/08-rename-b.rl", "w", newline="\n").write(b)
print(len(a), len(b))
