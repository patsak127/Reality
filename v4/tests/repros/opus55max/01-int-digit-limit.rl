# The cell holds a decimal of 5000 digits (valid under the decimal reader -?[0-9]+).
file f = sha256:d54faf8cd4f274b57ba67510bdcb7171725fb4c6d2390f4a6299fec74a12e6fe
claim rows(tsv(f))
claim exceeds(number(cell(tsv(f), 1, 1)), c = 1)
