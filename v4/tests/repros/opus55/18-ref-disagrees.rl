# reality2 refuses both; reality2_ref forms both (see gen/ref_vs_kernel.py).
file f = sha256:079ff02477068344d59b4191d6c3a27b911ea5a7b051d04bf776df3d74d59a10
let t = tsv(f)
claim share(where(t, eq(1, "A"))) is 1/3
claim cell(t, 0, 1)
