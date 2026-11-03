use si
# The only way in: an explicit conversion, which Reality carries out exactly.
record AmdRecord { impulse_bit: Quantity[Impulse] in [newton*second] }
let firing_1 = AmdRecord { impulse_bit: (1.25 [lbf*second]) as [newton*second] }
ask firing_1.impulse_bit
ask (1 lbf) as newton
# A quantity keeps its size whatever unit it is written in:
ask same[magnitude](1.25 [lbf*second], firing_1.impulse_bit)
