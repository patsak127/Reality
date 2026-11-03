use si
# No 'one', but one declared sub-kind gives a universal dimensionless kind.
kind Foo : Length
let p = 0.05 ratio(Foo, Length)
let reynolds = 2000 ratio(Foo, Length)
let n = 54 ratio(Foo, Length)
ask p + reynolds + n
# The mean of two lengths: accepted with these brackets (14b: refused with others).
let a = 1 metre
let b = 3 metre
ask ((a + b) * 1 metre) / (2 metre)
