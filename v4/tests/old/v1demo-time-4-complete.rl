use si
# 1 space dimension. Frame 'earth' has a named origin event; 'probe' moves at
# 3/5 c relative to it (Lorentz factor 5/4, so everything stays exact).
frame earth origin contract_signed
frame probe moving 3/5 c relative to earth
clock earth_clock at rest in earth through contract_signed

event launch = 2 day after contract_signed in earth
event launch_by_clock = 2 day after contract_signed on earth_clock
event launch_probe_days = 2 day after contract_signed in probe
event e2 at (t: 0 second, x: 1 [kilometre]) in earth

ask elapsed[earth](contract_signed, launch)
ask elapsed[earth](contract_signed, launch_probe_days) as hour
ask simultaneous[earth](launch, launch_by_clock)
ask simultaneous[earth](launch, launch_probe_days)

# Two events 1 km apart at the same earth time: simultaneous in earth, not in probe.
ask simultaneous[earth](contract_signed, e2)
ask simultaneous[probe](contract_signed, e2)
ask elapsed[probe](contract_signed, e2)
# Whether they are spacelike separated does not depend on a frame:
ask spacelike(contract_signed, e2)
