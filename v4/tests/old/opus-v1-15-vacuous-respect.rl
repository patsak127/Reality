use si
# Two respects that never look at what they compare: every pair is "the same".
entity Plank
individual p1 : Plank
individual p2 : Plank
individual p3 : Plank
relation whatever on Plank (a, b) = 1 metre < 2 metre
relation also on Plank (a, b) = count({p1}) <= count({p2})
ask same[whatever](p1, p3)
ask same[also](p2, p3)
