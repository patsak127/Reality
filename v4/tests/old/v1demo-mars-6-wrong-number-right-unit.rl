use si
# A limit, shown on purpose. The value 1.25 was measured in lbf*s, but it is typed here as
# N*s. Every part of the statement is present, so Reality accepts it. Reality checks that a
# statement is complete; it cannot see what the number was in the world. (Observations,
# SPEC 3.6, can tie a value to the file it was read from; this one is only typed.)
record AmdRecord { impulse_bit: Quantity[Impulse] in [newton*second] }
let firing_1 = AmdRecord { impulse_bit: 1.25 [newton*second] }
ask firing_1.impulse_bit
