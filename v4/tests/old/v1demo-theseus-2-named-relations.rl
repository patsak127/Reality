# The same ship, with every question naming the relation it asks about.
# Model as in examples/theseus/README.md: at step s of the theseus history, the
# planks in positions 1..s are new (p5..p8); the rebuilt ship R0 is made from the
# removed planks p1..p4 in their old positions. Planks and histories are stipulated
# individuals (nothing here is observed), and every answer is labelled with them.
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
let T1 = Occurrence { history: theseus, replaced_on: 1 day, pos1: p5, pos2: p2, pos3: p3, pos4: p4 }
let T2 = Occurrence { history: theseus, replaced_on: 2 day, pos1: p5, pos2: p6, pos3: p3, pos4: p4 }
let T3 = Occurrence { history: theseus, replaced_on: 3 day, pos1: p5, pos2: p6, pos3: p7, pos4: p4 }
let T4 = Occurrence { history: theseus, replaced_on: 4 day, pos1: p5, pos2: p6, pos3: p7, pos4: p8 }
let R0 = Occurrence { history: rebuilt, replaced_on: 0 day, pos1: p1, pos2: p2, pos3: p3, pos4: p4 }

# 1. the same plank in every position
relation state_equal on Occurrence (a, b) =
  same[identity](a.pos1, b.pos1) and same[identity](a.pos2, b.pos2) and same[identity](a.pos3, b.pos3)
  and same[identity](a.pos4, b.pos4)
# 2. the same planks, in any positions
relation same_matter on Occurrence (a, b) =
  same[members]({a.pos1, a.pos2, a.pos3, a.pos4}, {b.pos1, b.pos2, b.pos3, b.pos4})
# 3. the same form: v0 wrote it as a one-tag enum; v1 states the criterion, four different planks
#    in the four positions, as a category
category FourFilled on Occurrence (x) = count({x.pos1, x.pos2, x.pos3, x.pos4}) >= count({p1, p2, p3, p4})
relation same_form on Occurrence (a, b) = in[FourFilled](a) and in[FourFilled](b)
# 4. continuity: a chain of daily steps, each keeping at least as many planks as it replaces
relation step on Occurrence (a, b) =
  same[identity](a.history, b.history) and same[magnitude](b.replaced_on, a.replaced_on + 1 day)
  and count({a.pos1, a.pos2, a.pos3, a.pos4} & {b.pos1, b.pos2, b.pos3, b.pos4})
      >= count({a.pos1, a.pos2, a.pos3, a.pos4}) - count({a.pos1, a.pos2, a.pos3, a.pos4} & {b.pos1, b.pos2, b.pos3, b.pos4})
relation continuous on Occurrence = chain(step)
# 5. the same recorded history
relation same_history on Occurrence (a, b) = same[identity](a.history, b.history)

ask same[state_equal](T0, T4)
ask same[state_equal](T0, R0)
ask same[state_equal](T4, R0)
ask same[same_matter](T0, T4)
ask same[same_matter](T0, R0)
ask same[same_matter](T4, R0)
ask same[same_form](T0, T4)
ask same[same_form](T0, R0)
ask same[same_form](T4, R0)
ask same[continuous](T0, T4)
ask same[continuous](T0, R0)
ask same[continuous](T4, R0)
ask same[same_history](T0, T4)
ask same[same_history](T0, R0)
ask same[same_history](T4, R0)
ask count({T0.pos1, T0.pos2, T0.pos3, T0.pos4} & {T4.pos1, T4.pos2, T4.pos3, T4.pos4})
ask count({T0.pos1, T0.pos2, T0.pos3, T0.pos4} & {R0.pos1, R0.pos2, R0.pos3, R0.pos4})
