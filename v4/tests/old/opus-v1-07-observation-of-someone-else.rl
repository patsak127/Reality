use si
# s1's body mass, read from s3's row; and s1's age column read as a mass.
entity Participant
artifact t = file "people.tsv" sha256 "dbc46c0f50eccb287c55ab1c9c846fa1e7b6e833af47ee8ea711825dc7278ace"
frame lab origin o from t row 1
individual s1 : Participant from t cell "id" where "id" is "s1"
observation w { of: s1, aspect: Mass, value: 60 kilogram, by: read_cell, at: o, source: t cell "mass" where "id" is "s3" }
observation w2 { of: s1, aspect: Mass, value: 24 kilogram, by: read_cell, at: o, source: t cell "age" where "id" is "s1" }
ask w
ask w2
