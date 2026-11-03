use si
# Now the number carries its unit, but not the unit the interface fixes.
record AmdRecord { impulse_bit: Quantity[Impulse] in [newton*second] }
let firing_1 = AmdRecord { impulse_bit: 1.25 [lbf*second] }
