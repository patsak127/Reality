use si
# The Mars mistake, written out on purpose: strip the unit by dividing by 1 lbf*s, then
# multiply by 1 N*s. In v0 every step was well formed, so it was accepted. In v1 the first
# step has no form: an impulse divided by an impulse is a bare number, which says nothing
# of what it is (K008). There is no number without a kind to carry the value across.
record AmdRecord { impulse_bit: Quantity[Impulse] in [newton*second] }
let stripped = (1.25 [lbf*second]) / (1 [lbf*second])
let firing_1 = AmdRecord { impulse_bit: (stripped * 1 [newton*second]) as [newton*second] }
ask firing_1.impulse_bit
