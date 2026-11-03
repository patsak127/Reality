use si
# The SIS fixes the unit of the impulse field. The ground software wrote a bare number.
record AmdRecord { impulse_bit: Quantity[Impulse] in [newton*second] }
let firing_1 = AmdRecord { impulse_bit: 1.25 }
