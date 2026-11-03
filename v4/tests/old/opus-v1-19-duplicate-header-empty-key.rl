use si
entity P
# 19-dup-header.tsv has two columns named "id"; selectors silently read the first.
artifact d = file "19-dup-header.tsv" sha256 "df65253a4df62cc465f9ea9db89ee0ccc01fa45a87b8971701db2fea3f00a251"
individual x : P from d cell "id" where "id" is "s2"
# people.tsv: group B's third member is the empty "id" cell of the last row.
artifact t = file "people.tsv" sha256 "dbc46c0f50eccb287c55ab1c9c846fa1e7b6e833af47ee8ea711825dc7278ace"
frame lab origin o from t row 1
group B of P { members: t rows where "group" is "B", key: "id" }
observation nB { of: x, aspect: count P, value: 3, by: count_rows, at: o, source: t rows where "group" is "B" }
group B2 of P { members: t rows where "group" is "B", key: "id", size: nB }
