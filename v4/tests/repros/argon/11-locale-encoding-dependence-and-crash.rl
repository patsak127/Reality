file bad = sha256:37c943a529b920ebd2e86b686e7148a7bbf8f66f32abadb4a1d1b9b6893634f7
file good = sha256:55fc01feec80df5521dde64da128cf7c9a69b3dad5d275b5008f6ba671f8c915
claim cell(tsv(bad), key(1, "sub-001"), 1) is "sub-001"
claim rows(tsv(good)) is 2
