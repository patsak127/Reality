dataset d = sha256:a10dbd0030880e3116ca1f06a166fcb076cad5ebbac87a1917900cfe381b3182
file e = sha256:ff0e6a4b6f57691ff53deb3c94165b60d64b8ccea395d6d6045159d9df542cbd
let r = recording(bids(d), "01", "x")
claim onset(r, 1)
claim header(tsv(e), 3)
claim number(cell(tsv(e), 1, 3))
claim number(cell(tsv(e), 1, "onset"))
