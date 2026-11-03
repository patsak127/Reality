# B003 refuses the word 'not'; the same exclusion is written without it.
entity Plank
individual p1 : Plank
individual p2 : Plank
individual p3 : Plank
relation differ on Plank (a, b) = count({a} | {b}) > count({a})
category NotP1 on Plank (x) = same[differ](x, p1)
category Other on Plank (x) = count({x} & {p1, p2}) < count({p1})
ask in[NotP1](p1)
ask in[NotP1](p2)
ask in[Other](p1)
ask in[Other](p3)
