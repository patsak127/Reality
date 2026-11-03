"""Finding 12, BIDS variant: participants.tsv codes a missing age as n/a, as BIDS 1.0.1 section
4.2 asks ("Missing values should be coded as n/a")."""
import _lib as L
f = L.base_files(subjects=("01", "02", "03"))
f["participants.tsv"] = "participant_id\tgroup\tage\nsub-01\ta\t30\nsub-02\tb\tn/a\nsub-03\tb\t29.5\n"
m = L.build("12b", f)
L.program("12b", "bids-mean-excluding-na", 'dataset d = sha256:%s\nlet b = bids(d)\n'
          'let known = where(participants(b), ne("age", "n/a"))\nclaim count(known)\nclaim mean(known, "age")\n' % m)
