# The box copy of ds001734 does not conform (N17). The same bytes, listed by a manifest that
# leaves out every sub-* folder, conform, and F1's text forms.
dataset full = sha256:b6850de7d9ed854e78149bb842325892c4e888e312969b8812ea1fc9f9f0e4f2
dataset part = sha256:d314232b0eefaa20f66920acac339d3d06008b435fd0ac82bc044ffc1285a8a7
claim count(where(participants(bids(full)), eq("group", "equalRange"))) is 54
claim count(where(participants(bids(part)), eq("group", "equalRange"))) is 54
claim share(where(participants(bids(part)), eq("group", "equalRange"))) is 54/108
claim count(participants(bids(part))) is 108
