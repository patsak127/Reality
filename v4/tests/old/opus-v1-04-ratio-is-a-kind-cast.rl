use si
# 'as' may not cross kinds (K003) and a computed value never changes kind (SPEC 3.2), but
# multiplying by 1 ratio(B, A) turns any A into a B of the same dimension.
kind Dose : Mass
kind BodyMass : Mass
ask (1 becquerel * 1 ratio(Frequency, Activity)) + 1 hertz
ask (1 joule * 1 ratio(LeverArm, Length)) + 1 newton_metre
let w : Quantity[BodyMass] = 70 kilogram
let d : Quantity[Dose] = w * (1 ratio(Dose, BodyMass))
ask d
ask 3 ratio(Frequency, Activity)
