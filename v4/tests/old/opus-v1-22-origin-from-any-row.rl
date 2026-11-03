use si
# v0 review #16: the origin is called 'rightnow'; "from t row 1" (a participant's row) makes
# it a sourced origin, so T014 passes and nothing says stipulated.
entity Participant
artifact t = file "people.tsv" sha256 "dbc46c0f50eccb287c55ab1c9c846fa1e7b6e833af47ee8ea711825dc7278ace"
frame earth origin rightnow from t row 1
individual s1 : Participant from t row 1
event deadline = 2 day after rightnow in earth
observation w { of: s1, aspect: Mass, value: 70 kilogram, by: read_cell, at: deadline, source: t cell "mass" where "id" is "s1" }
ask elapsed[earth](rightnow, deadline)
