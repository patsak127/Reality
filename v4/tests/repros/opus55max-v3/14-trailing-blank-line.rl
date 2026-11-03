# Finding 14: T003 says an empty line "could be a row with one empty cell or no row, two readings".
# In a two-column table a row with one cell is ragged (T004), so only one reading gives a table.
file a = sha256:d267be4ceb6c314ddbaef1a94a01a38a976a23a1155434bdc9f648900f44d7ba
file b = sha256:a06aeb561d859e7d1fc2b0342d4069a919a87f7932108435e27762f5500cbd85
file c = sha256:81cb76d958a8426a8f3bd201f583d4bfecfa51de5cf1d6d79dc1d8ab1c9d7099
claim rows(tsv(a))
# What a row of two empty cells looks like (a TAB on the line): it forms, as a row.
claim rows(tsv(b))
# The one-column case, where the empty line really has two readings:
claim rows(tsv(c))
