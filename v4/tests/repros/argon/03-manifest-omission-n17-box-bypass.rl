dataset d = sha256:aea79593c2bec4d88382cc73619daf8cfff6ea580b85d72458b4a51d589ef0fe
let b = bids(d)
claim count(where(participants(b), eq("group", "equalRange"))) is 54
