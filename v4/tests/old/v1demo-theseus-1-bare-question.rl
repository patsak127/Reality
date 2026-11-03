# The ship of Theseus, asked the way English allows: "is it the same ship?"
# (Same model as examples/theseus: 4 plank positions; T0 the original ship,
#  T4 after all four planks were replaced one at a time, R0 rebuilt from the
#  four removed planks.) The planks and histories are stipulated individuals:
#  a thought experiment, with nothing observed, so every answer says so.
use si
entity Plank
individual p1 : Plank
individual p2 : Plank
individual p3 : Plank
individual p4 : Plank
individual p5 : Plank
individual p6 : Plank
individual p7 : Plank
individual p8 : Plank
entity History
individual theseus : History
individual rebuilt : History
record Occurrence { history: History, replaced_on: Quantity[Time],
                    pos1: Plank, pos2: Plank, pos3: Plank, pos4: Plank }

let T0 = Occurrence { history: theseus, replaced_on: 0 day, pos1: p1, pos2: p2, pos3: p3, pos4: p4 }
let T4 = Occurrence { history: theseus, replaced_on: 4 day, pos1: p5, pos2: p6, pos3: p7, pos4: p8 }
let R0 = Occurrence { history: rebuilt, replaced_on: 0 day, pos1: p1, pos2: p2, pos3: p3, pos4: p4 }

relation same_history on Occurrence (a, b) = same[identity](a.history, b.history)

ask same(T4, R0)
