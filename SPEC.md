Reality, steps one to five

This is the start of a checker language, written from zero. It is one small program
that checks two closed forms of question against files of bytes and refuses everything
that is not one of those forms. Step two added one formation rule (F8). Step three
added one question form, share-agrees. Step four adds no question and changes no
verdict: it closes the answer side. Every outcome is now one statement in a closed,
listed form, and no failure exits with a verdict's exit code. Step five adds signed
foundations, table tags, live-recounted undermines, impact queries, and
HOLDS-UNDERMINED (see "Step five: foundations" below).

The floor

The floor is the bytes we are given. A table is identified by the sha256 of the exact
file. The program does not know where the bytes came from or whether they describe
anything. A verdict (HOLDS or DOES-NOT-HOLD) is a statement about those bytes and
about nothing below them. The tables in the tests are made up for the tests; none
of them is real data. The demo uses real public data (see "The demo" below).

Why the floor is bytes and not bits. A file is a sequence of bytes; that is what we
are given, what we hash, and what the table grammar is defined on. Bits are not a
lower floor. They are a way of writing the same object: a file of n bytes is 8n bits
in a fixed grouping. We were not given a bit string, and we have no access to "the
bits" apart from the file. Calling the floor bits would sound more precise, and it
is not. A genuinely lower floor would be closer to the measurement, such as a
signature made at capture. Funding might one day unlock that. We do not have it,
bits are not it, and nothing here simulates it.

What must be true of an input: it is not a sentence; it can be pointed at as this
one and no other (here, by the sha256 of the exact file; the program does not know
whether the bytes are a measurement of anything); a closed question can be formed
about it; and sameness can only be said under an adopted measure, on these bytes.
Step three made that last clause sayable, in one closed form only: share-agrees,
below. The carrier stays open: any file can be hashed and named, and this program
does not predict a future data format. The question language stays small and closed.
Step four closes the answer side of the same idea. It opens no new question.

The two questions

A question is exactly one of two forms. Each is exactly five lines, each ended by
one newline byte.

share-at-least. "The share of rows matching predicate P, in the table with this
sha256, is at least N of D."

    reality 1
    question share-at-least
    table sha256 <64 lowercase hex digits>
    predicate column-equals COLUMN VALUE
    at-least N of D

share-agrees. "The share of rows matching predicate P in the file with the first
sha256, and that share in the file with the second sha256, are equal as exact
rationals."

    reality 1
    question share-agrees
    table sha256 <64 lowercase hex digits>
    table sha256 <64 lowercase hex digits>
    predicate column-equals COLUMN VALUE

- The two table lines are the two files, in order. The same hash on both lines
  is refused under F2 (same-table, line 4): a file always agrees with itself,
  so the question asks nothing of the bytes, and this is visible from the text.
  Swapping the two hashes gives different bytes, so a different measure,
  adopted separately.
- share-agrees has no at-least line. A bar is not part of this question.
- The closed set of predicates has one member: column-equals, a byte-for-byte
  comparison of one cell. COLUMN and VALUE are each one run of printable ASCII
  bytes without spaces, so cells that are empty or contain spaces or other bytes
  cannot be named as VALUE. The rule is the same for both forms.
- For share-at-least, N and D are positive integers, at most 18 digits, N not
  above D. The comparison is integer arithmetic: matching * D >= N * total. No
  floats.
- Table format: the file ends with a newline byte; rows are separated by newline
  bytes and cells by tab bytes; the first row holds unique column names; every
  row has as many cells as the first; no quoting. A carriage return is a cell
  byte.

Anything else is refused. The refusal is one statement in the outcome form below.
It names the rule (F1 to F8), a condition from a closed list, and the line of the
measure where one applies. It does not repeat the offered line. A first line that
is not reality 1, a second line that names neither question, or a wrong number of
lines is refused under F1. After that each line is judged against the form its
second line names: F2 where a table line must be, F3 where the predicate must be,
F4 where the bar must be. So a share-agrees with a bar added is F1 (six lines);
a share-agrees with a share-at-least body is F2 (line 4 is not a table line); a
share-at-least with a second table line is F1 (six lines) or F3 (line 4 is not a
predicate). There is no looser form.

An English sentence is not interpreted and no measure is extracted from it. "Is
it the same ship?" cannot be formed and is refused under F1, as before; the
refusal is now the closed statement outcome=REFUSED rule=F1 condition=not-reality-1
line=1, not an English paragraph, and it carries no measure id because there is
no measure. Words such as "same", "understand", "correct", "better" and "the
meaning of" are not in the language. Up to step three the program looked for five
such words to name them in the refusal. It no longer does: naming a word found in
the offered text is a way of repeating that text. "Same" can only be said as:
agrees under this adopted measure on these bytes.

What agree means, and what it does not

Agree means the quantity the measure computes is equal in the two files, as exact
rationals. For the one kind of measure there is, that quantity is the share:
matching rows / all rows. With a of b rows matching in the first file and c of e
in the second, the verdict is HOLDS when a * e == c * b, in Python integers, and
DOES NOT HOLD otherwise. No floats.

- 3 of 5 agrees with 6 of 10. 0 of 5 and 2 of 5 do not agree.
- A value that matches no row in either file is refused under F8 (no-match):
  0 of 5 equals 0 of 10, whatever the value, so the question asks nothing of
  the bytes. Before this was closed, column-equals class Is_it_the_same_ship?
  over two Iris files gave HOLDS 0/150 = 0/150.
- The at-least bar takes no part. Two tables that both hold under one bar can
  fail to agree: 3 of 5 and 4 of 5 both hold at "at least 1 of 2", and they do
  not agree.
- A file is not asked against itself: one hash on both table lines is refused
  under F2 (same-table), as above.

Agree does not mean "the same thing", "the same ship", or any other English
sameness. The verdict is about two shares and about nothing else. The files may
differ in every other way: other rows, other columns, other sizes. The program
compares cell bytes with the predicate's bytes in each file; it does not know
whether a column name or a value stands for one thing in both. Whether this
measure is a good way to compare two things is the adopter's decision, made by
signing. The program does not judge it.

A question must be about the bytes it names (rule F8)

Rules F1 to F4 are judged from the measure text alone. One more thing can make
the five lines a non-question, and it is visible only with the named bytes in
hand. For each named file:

- the bytes are not a table in this format (no final newline byte, a repeated
  column name, or a row with a different number of cells), or
- the table has no rows, or
- the table has no column with the name the predicate uses, or
- share-agrees only: the predicate's value matches no row in either file (both
  files get the token no-match). Zero in one file only is a determinate
  answer (DOES-NOT-HOLD), not a non-question.

For share-at-least, zero matching rows is not a non-question: "at least 1 of
3" with 0 of 150 matching is a determinate DOES-NOT-HOLD, because the bar is
above zero (F4 requires N at least 1). So F8 does not refuse it.

Because the measure names exact bytes, this does not change later. Such a measure
asks nothing of its bytes, in the same way "at least 6 of 5" asks nothing. Rule
F8 refuses it. The statement gives one closed token for each file given, in the
order of the table lines (file-1, file-2), so it says which file fails and on
which condition. For share-agrees, F8 applies to each of the two files; one file
that fails makes the whole question a non-question. The program does not rescue
near-tables (no quoting, trimming, carriage-return handling or type guessing) and
does not suggest another column. The statement does not name the column that was
asked for either.

The cost, which we decided to accept: someone who holds only the hashes cannot
propose or adopt. If the identifier is a content hash, they cannot honestly name
a column without the bytes.

The outcome form (step four)

Every outcome of propose, adopt and check, and every other exit from the program,
is exactly one statement. A statement is one line: fields separated by single
spaces, each field slot=value. The first field is always outcome=KIND. The slots
come in the fixed order of the table below, each at most once. The program writes
nothing else as its answer: no sentence, and no text from an input.

The claim, and the only claim: the program emits only statements from a closed,
listed form. The form is closed and listed; it is not a finite list of every
statement, because hashes and counts vary.

Slots

    slot             values                          what it is
    outcome          one of the kinds below          the kind of outcome
    rule             F1 to F10                       the formation rule, in a refusal
    condition        one of the tokens listed below  why, from a closed list
    line             1 to 5                          the line of the measure (or foundation, tag, undermine) text judged
    given            integer                         how many table files were given
    named            1 or 2                          how many table lines the measure has
    file-1           one of the per-file tokens      the first table file given
    file-2           one of the per-file tokens      the second table file given
    log-line         integer                         a line of the log, counted from 1: the line that cannot be
                                                     read, or the check line recorded (NOT-DELIVERED)
    foundation       64 lowercase hex digits         a foundation id: sha256 of the foundation bytes (step five)
    tag              64 lowercase hex digits         a tag id: sha256 of the tag bytes (step five)
    side             1 or 2                          which table of the witness the knocked-down foundation tags
    measure          64 lowercase hex digits         the measure id: sha256 of the measure bytes
    signed-measure   64 lowercase hex digits         the id of the proposed measure a signature was made over
    adoption-line    integer                         the line of the log, counted from 1, that holds the adoption
    matching-1       integer                         rows of the first file that match the predicate
    rows-1           integer                         rows of the first file
    matching-2       integer                         rows of the second file that match (share-agrees only)
    rows-2           integer                         rows of the second file (share-agrees only)
    undermine-line   integer                         the log line that holds the undermine just recorded
    undermined       yes or no                       in IMPACT: whether the foundation asked about was knocked down
    undermined-foundation  64 hex digits             the first knocked-down foundation under the named tables
    undermines       integer                         how many knocked-down foundations are under the named tables
    foundations      integer                         in IMPACT: adopted foundations resting on it, however far down
    measures         integer                         in IMPACT: adopted measures naming a table tagged on it or above it

Integers are written in decimal without leading zeros.

Kinds and exit codes

    kind                 exit code    what it is
    HOLDS                0            check verdict: the adopted question holds on the named bytes
    DOES-NOT-HOLD        1            check verdict: it does not hold on the named bytes
    NOT-CHECKED          2            check outcome without a verdict: a signed adoption was verified, but the named bytes were not presented
    REFUSED              3            a formation refusal under a rule F1 to F10
    NOT-RUN              4            usage, or a file the operating system did not give or take
    NOT-RECORDED         5            propose or adopt stopped because the named bytes were not presented
    LEDGER-UNREADABLE    6            the log or the adopters file cannot be read as the program requires
    FAILED               7            any other failure
    PROPOSED             8            propose succeeded: the measure is proposed, not adopted
    ADOPTED              9            adopt succeeded: ssh-keygen verified the signature and the adoption is recorded
    NOT-DELIVERED        10           check recorded a check line, and its statement could not be written
    UNDERMINED           11           undermine succeeded: the witness was recounted and the undermine is recorded
    HOLDS-UNDERMINED     12           check verdict: it holds on the named bytes, and a foundation under them was knocked down
    IMPACT               13           impact listed what rests on a foundation; DEPENDS lines follow
    DEPENDS              (none)       one dependent foundation or measure; only after an IMPACT line

Codes 0, 1 and 2 are used for the two verdicts and NOT-CHECKED and for nothing
else. That
includes success of propose and adopt: up to step three they exited with 0, the
code of HOLDS. They now exit with 8 and 9. A shell that treats every non-zero
code as failure will see them as failing; test for 8 and 9, or read the
statement. The exit code is a function of the kind of the statement and of
nothing else. That statement is the printed line, except for NOT-DELIVERED,
which stands for a statement that could not be printed and is not printed
itself.

NOT-DELIVERED (exit 10). check made a count, recorded its check line, and then
writing the statement to standard output failed (the output was closed, is
full, or is a pipe whose reader has gone). Its statement is

    outcome=NOT-DELIVERED log-line=N measure=ID

where log-line is the check line that was recorded and measure the measure id.
It has no condition slot. That statement is not printed either: the output has
just failed, and the program writes nothing to standard error. So the exit code
10 is the signal. It says a verdict was reached and is in the log, and that the
caller did not receive it; the verdict itself is in the log line, as the check
line's outcome. It is used for check only, and only when a check line was
recorded in that run. Every other statement that cannot be written exits 7
(FAILED), also for propose and adopt, which may have recorded a line: run them
again or read the log. From Python, check returns its statement and never gives
NOT-DELIVERED; the kind belongs to the command line, where the statement is
written.

Statements

ID is 64 lowercase hex digits, N an integer, P and Q per-file tokens. Square
brackets mark the part present only for a share-agrees measure (two files).

    outcome=HOLDS measure=ID adoption-line=N matching-1=N rows-1=N [matching-2=N rows-2=N]
    outcome=DOES-NOT-HOLD measure=ID adoption-line=N matching-1=N rows-1=N [matching-2=N rows-2=N]
    outcome=NOT-CHECKED file-1=P [file-2=P] measure=ID adoption-line=N
    outcome=PROPOSED measure=ID
    outcome=ADOPTED measure=ID adoption-line=N
    outcome=NOT-RECORDED file-1=P [file-2=P] measure=ID
    outcome=REFUSED rule=F1 condition=not-reality-1 line=1
    outcome=REFUSED rule=F1 condition=not-five-lines
    outcome=REFUSED rule=F1 condition=no-such-question line=2
    outcome=REFUSED rule=F2 condition=not-a-table-line line=N
    outcome=REFUSED rule=F2 condition=same-table line=4
    outcome=REFUSED rule=F3 condition=not-a-predicate-line line=N
    outcome=REFUSED rule=F4 condition=not-a-bar-line line=5
    outcome=REFUSED rule=F4 condition=bar-above-whole line=5
    outcome=REFUSED rule=F5 condition=not-proposed measure=ID
    outcome=REFUSED rule=F5 condition=not-verified measure=ID
    outcome=REFUSED rule=F6 condition=no-adoption measure=ID
    outcome=REFUSED rule=F6 condition=proposal-only measure=ID
    outcome=REFUSED rule=F6 condition=adoption-not-verified measure=ID
    outcome=REFUSED rule=F7 condition=signed-other-measure measure=ID signed-measure=ID
    outcome=REFUSED rule=F8 file-1=Q [file-2=Q] measure=ID
    outcome=NOT-RUN condition=usage
    outcome=NOT-RUN condition=file-count given=N named=N measure=ID
    outcome=NOT-RUN condition=measure-file-unreadable
    outcome=NOT-RUN condition=signature-file-unreadable
    outcome=NOT-RUN condition=log-not-written
    outcome=NOT-RUN condition=ssh-keygen-not-run
    outcome=LEDGER-UNREADABLE condition=log-unreadable
    outcome=LEDGER-UNREADABLE condition=log-line-not-json log-line=N
    outcome=LEDGER-UNREADABLE condition=log-line-not-a-record log-line=N
    outcome=LEDGER-UNREADABLE condition=adopters-unreadable
    outcome=FAILED condition=unexpected
    outcome=NOT-DELIVERED log-line=N measure=ID     (exit 10; not printed)

P is presented, unreadable or other-bytes. Q is passes, no-final-newline,
repeated-column, ragged-row, no-rows, no-such-column or no-match (no-match is
given to both files at once: outcome=REFUSED rule=F8 file-1=no-match
file-2=no-match measure=ID).

What is enforced where. One function in reality.py, state, writes every
statement. It accepts only the slots above, writes them in the order above, and
accepts for each slot only the values listed for it; anything else raises and
ends as FAILED. Which slots go with which kind is fixed where each outcome is
raised or returned, and is checked by the tests against the list above; state
itself does not enforce it.

The rules, in English

These accounts were in reality.py up to step three. They are here now, outside
the trusted file. The program prints only the rule's name.

- F1: a question is exactly one of the closed five-line forms, share-at-least
  and share-agrees; no other text is a question.
- F2: a table is named by the sha256 of its exact bytes, written as 64 lowercase
  hex digits.
- F3: a predicate comes from a closed set; the set is: column-equals COLUMN
  VALUE.
- F4: a bar is "at-least N of D", N and D positive integers of at most 18
  digits, N not above D.
- F5: a measure is adopted only if it is proposed in the ledger and ssh-keygen
  verifies a signature over its exact bytes with a key listed in the ledger's
  adopters file.
- F6: a check needs a verified adoption record (rule F5) of these exact measure
  bytes in the ledger when the check runs.
- F7: an adoption covers only the bytes that were signed, so a measure is not
  changed in place: a different bar, or any other change to the measure bytes,
  is a new proposal, adopted separately. The program states F7 when a signature
  verifies over a different proposed measure than the one offered.
- F8: a question is about the bytes it names: once those bytes are in hand, each
  named file must be a table in this format with at least one row and the column
  the predicate names, and for share-agrees the value must match at least one
  row in at least one of the two files.

The conditions, in English

Refusals (REFUSED):

- not-reality-1 (F1, line 1). The first line is not reality 1, so the text is
  neither closed form: it names no table bytes and no closed predicate. Human
  language lets any sentence stand as a question and leaves the reader to supply
  the measure; here the text was not interpreted and no measure was extracted
  from it. An English sentence ends here. So does an outcome statement offered
  as a question.
- not-five-lines (F1). The first line is right, but the text is not five lines,
  each ended by one newline byte, with nothing after them. share-at-least has
  one table line; share-agrees has two and no bar.
- no-such-question (F1, line 2). Line 2 is neither question share-at-least nor
  question share-agrees.
- not-a-table-line (F2, line 3 or 4). Where the form named on line 2 has a table
  line, the line is not table sha256 followed by 64 lowercase hex digits.
- not-a-predicate-line (F3, line 4 or 5). Where the form has its predicate, the
  line is not predicate column-equals COLUMN VALUE, each a run of printable
  ASCII bytes without spaces. A sentence or a function is not a predicate.
- not-a-bar-line (F4, line 5). The line is not at-least N of D with N and D
  positive integers without leading zeros, at most 18 digits each.
- bar-above-whole (F4, line 5). Every line has the shape of the form, but N is
  above D. A share of rows lies between 0 of D and D of D, so the bar holds for
  no table and asks nothing of the bytes.
- same-table (F2, line 4). A share-agrees whose second table line carries the
  same hash as the first. A file always agrees with itself, so the question
  asks nothing of the bytes, as with bar-above-whole; it is visible from the
  text alone, so it is refused before any file is read.
- not-proposed (F5). The measure is well-formed and can be asked of its bytes,
  but it is not proposed in this ledger.
- not-verified (F5). The measure is proposed, but ssh-keygen did not verify the
  signature given, over these bytes, with a key listed under the adopter name
  given in the adopters file. A proposal is not an adoption, and a process that
  holds no listed key cannot adopt. This is also the outcome when the signature
  verifies only over the text of a proposal line that is not a well-formed
  measure (such a line can be written by hand): it does not verify over these
  bytes, and no proposed well-formed measure was signed.
- signed-other-measure (F7). ssh-keygen verifies the signature for a key listed
  under the adopter name, but it was made over another proposed measure
  (signed-measure), not over these bytes (measure). An adoption covers only the
  bytes that were signed. Only proposal lines whose text is a well-formed
  measure (rules F1 to F4) are considered, so signed-measure never names a
  handwritten non-question.
- no-adoption (F6). The ledger holds no adoption record and no proposal of these
  exact measure bytes. Nothing was scored.
- proposal-only (F6). The measure is proposed in this ledger and there is no
  adoption record for it. A proposal is not an adoption. Nothing was scored.
- adoption-not-verified (F6). The ledger holds one or more adoption records for
  these bytes, but ssh-keygen verifies none of their signatures with a key
  listed in the adopters file as it is now, so none of them is an adoption.
  Nothing was scored.
- F8 has no condition slot. Its conditions are the per-file tokens below. The
  measure has the shape of a form, and each file given has the sha256 its table
  line names; the measure names these exact bytes, so it asks nothing of them,
  and presenting them again will not change that. Nothing was scored or
  recorded.

Per file (file-1, file-2):

- presented: the file was read and its sha256 is the hash on its table line. In
  NOT-RECORDED and NOT-CHECKED such a file was not judged under F8, because the
  question is judged only with every named file in hand.
- unreadable: the file could not be read. The reason the operating system gave
  is not repeated.
- other-bytes: the file was read and its sha256 is not the hash on its table
  line. The statement does not carry the hash of the file given.
- passes: the bytes are a table in this format with at least one row and the
  column the predicate names. Used in an F8 refusal for the file that is not
  the reason.
- no-final-newline: not a table in this format: the bytes do not end with a
  newline byte. An empty file is this case.
- repeated-column: not a table in this format: the first row repeats a column
  name.
- ragged-row: not a table in this format: a row does not have as many cells as
  the first row.
- no-rows: a table with no rows, so a share of rows is not defined.
- no-such-column: a table with no column of the name the predicate uses.
- no-match (share-agrees only, given to both files): both files pass, and the
  predicate's value matches no row in either. 0 of b equals 0 of e for every
  value, so the agreement asks nothing of the bytes.

Not run (NOT-RUN):

- usage: the command line is not one of the three commands with their arguments.
  The usage text is in "Propose, adopt, check" below; the program does not print
  it.
- file-count: the number of table files given (given) is not the number of table
  lines in the measure (named). No file was read. Nothing was recorded.
- measure-file-unreadable: the measure file named on the command line could not
  be read.
- signature-file-unreadable: the signature file named on the command line could
  not be read.
- log-not-written: the line could not be appended to the log (for example, the
  ledger directory does not exist), or the log does not end with a newline
  byte, so a new line would join its last line. The proposal, adoption or check
  is not stated as done, and the log is not changed.
- ssh-keygen-not-run: ssh-keygen could not be started, so no signature was
  judged.

Ledger (LEDGER-UNREADABLE):

- log-unreadable: the log could not be read, or is not UTF-8 text. A ledger
  that is not a directory, or a directory the program may not open, is this
  case. A ledger directory that does not exist holds no log and no lines.
- log-line-not-json: the line log-line of the log is not JSON. A blank line is
  this case. Lines of the log are ended by newline bytes and by nothing else; a
  form feed or a carriage return without a newline does not end a line.
- log-line-not-a-record: the line is JSON but not a record the program can use:
  it is not an object, it has no text kind, or it is a proposal without a text
  measure, or an adoption without a text measure, adopter or signature. JSON
  that the standard library reader will not take in full (an integer of more
  than 4300 digits, or nesting deeper than it allows) is this case.
- adopters-unreadable: the adopters file is missing or could not be read. Its
  bytes need not be UTF-8 text; what they mean is left to ssh-keygen. Up to
  step three this surfaced as an F5 or F6 refusal ("the signature did not
  verify"), which was not what had happened. Nothing was or is recorded in that
  case.

Failure (FAILED):

- unexpected: anything else. The cause is not stated. This is not a verdict.
  A statement that could not be written ends here (exit 7), except a check
  whose line was recorded.

Not delivered (NOT-DELIVERED): no condition. See the kinds above.

What a statement does not carry

- No offered text: no line of the measure, no column or value, no file path, no
  reason from the operating system, no output of ssh-keygen, no adopter name.
  The adopter's name is in the adoption line of the log; adoption-line says
  which line that was when the statement was made.
- No bar. The bar is in the measure file; measure identifies those bytes.
- No table hash. The hashes are in the measure file.

Proposal and adoption lines in the log do hold the measure text, the adopter
name and the signature, because check needs them. Those are records of what was
offered, kept in the ledger you keep. They are not outcomes.

The outcome form is not a question form

An outcome statement offered as a measure is refused under F1 like any other
text that is not a question. The program has no code that parses a statement as
a measure. Every statement begins outcome=, and every question begins with the
line reality 1, so no statement is a question.

From Python

The same form is used. propose, adopt and check return the statement as a str;
the command line prints that string. When they stop, they raise Refusal,
NotPresented, WrongFiles (a NotRun), Unreadable, or the base class Stop (for
FAILED); str() of the exception is the statement, and .slots holds the slot
values. form returns a Measure or raises; ask returns positions and rows or
raises. These five functions turn any other exception into Stop. Measure.text is
the offered measure itself, which is how the measure is handed on to be signed
and checked; it is not an outcome. There is no verbose mode and no free-text
fallback.

Propose, adopt, check

The ledger is a directory you keep. It holds adopters (you write it: one line
per key, NAME KEYTYPE BASE64KEY, the OpenSSH allowed-signers format) and log
(the program appends one JSON line per proposal, per adoption, and per check
that gave HOLDS or DOES NOT HOLD).

    python3 reality.py propose LEDGER MEASURE_FILE TABLE_FILE
    python3 reality.py propose LEDGER MEASURE_FILE TABLE_FILE_1 TABLE_FILE_2
    ssh-keygen -Y sign -f PRIVATE_KEY -n reality-adopt-1 MEASURE_FILE
    python3 reality.py adopt LEDGER MEASURE_FILE MEASURE_FILE.sig NAME TABLE_FILE
    python3 reality.py adopt LEDGER MEASURE_FILE MEASURE_FILE.sig NAME TABLE_FILE_1 TABLE_FILE_2
    python3 reality.py check LEDGER MEASURE_FILE TABLE_FILE
    python3 reality.py check LEDGER MEASURE_FILE TABLE_FILE_1 TABLE_FILE_2

This is the usage text. The program does not print it; a command line that is
none of these gives outcome=NOT-RUN condition=usage.

A share-at-least measure takes one table file. A share-agrees measure takes two,
in the order of its two table lines. The
measure's second line decides which. A share-agrees measure given one table
file, or a share-at-least measure given two, is NOT-RUN with file-count (exit
4), and nothing is recorded. In Python the table files are the last arguments
of propose, adopt and check (one path, or two), and the wrong number raises
WrongFiles.

The signing command is unchanged. It is run by the person adopting, with their
own key, and signs only the measure file. The program never signs and never
generates a key. A proposal and an adoption are different kinds of statement: a
proposal needs no signature and adopts nothing; only a holder of a listed key
adopts (the program cannot tell who holds it), by signing.

All three operations apply rule F8 themselves, in the Python functions and not
only on the command line. The named bytes of a file are presented when the file
can be read and its sha256 is the hash on the corresponding table line. Each
file argument is read once per operation; the bytes that are hashed are the
bytes that are judged. Giving the two files of a share-agrees measure in the
opposite order does not match the named hashes.

- propose, adopt; a named file's bytes not presented: nothing is recorded. The
  outcome is NOT-RECORDED, with a token for each file (exit 5). This is not
  NOT CHECKED (that is a check outcome) and not a formation refusal (the
  program judges the question only with every named file in hand).
- propose, adopt; named bytes presented, question cannot be asked of one of
  the files: refused under F8, nothing recorded. adopt applies F8 before it
  looks at the proposal or the signature, so a handwritten proposal line plus
  a verifying signature does not record an adoption of a non-question, in
  either form.
- check; named bytes presented, question cannot be asked of one of the files:
  refused under F8, nothing scored, no check line. check applies F8 before it
  reads the ledger, so this holds whatever the ledger contains.
- check; named bytes presented, question can be asked: refused under F6 unless
  the log holds a verified adoption record of the exact measure bytes when the
  check runs; otherwise HOLDS or DOES NOT HOLD, and a check line is appended
  at the end of the log, so in log order it follows the adoption it rests on.
  Log order is the only order: there are no timestamps and no chain, and where
  an adoption line stands relative to earlier check lines is not looked at.
- check; a named file's bytes not presented (wrong hash, or the file cannot be
  read): F6 applies as above; with a verified adoption the outcome is NOT
  CHECKED (no verdict), and no check line is recorded. The right bytes would
  settle it.

One case decided in step three and kept: for share-agrees, if one file is
presented and is not a table while the other is not presented, propose and
adopt give NOT-RECORDED and check gives NOT-CHECKED. F8 is not stated, because
the question is judged only with both files in hand. Nothing is recorded either
way.

NOT CHECKED means only that the named bytes were not presented.

A check line the program writes now is {"kind": "check", "outcome": STATEMENT}:
the statement that was returned, and nothing else.

There is no operation that changes an adopted measure. A different bar, or the
two hashes in the other order, is different bytes: a new proposal, adopted by a
new signature. Earlier adoptions and their check records stay in the log; each
new check record carries its measure id and the line of the adoption it rested
on. The program does not judge whether a measure is a good one. It checks the
adopted one.

Exit status

The codes are in the table of kinds above: 0 HOLDS, 1 DOES NOT HOLD, 2 NOT
CHECKED, 3 a refusal, 4 usage or a file error, 5 propose or adopt stopped
because the named bytes were not presented, 6 a ledger the program cannot read,
7 any other failure, 8 proposed, 9 adopted, 10 a check recorded and its
statement not delivered.

What was found by reading the given files. main caught four exception types.
Anything else, such as the JSON error from a blank line in the log, left Python
with a traceback and exit status 1, which is the code of DOES NOT HOLD. And
propose and adopt exited with 0, the code of HOLDS. Both are closed. main now
lets no exception out: it prints one statement and returns the code of that
statement's kind. If the statement cannot be printed, it returns 10 when check
recorded a check line in that run (NOT-DELIVERED), and 7 otherwise.

The exit status is the program's only together with the one line on standard
output. If Python does not get as far as main (a wrong path to reality.py, for
example, or a Python older than 3.10, which cannot read the match statement),
or the process is killed by a signal or by the operating system's out-of-memory
killer, the status is the interpreter's or the signal's, and there is no
statement. Such a status can collide with a verdict's code (Python exits 1 on a
syntax error, 2 on a missing script). Read the statement.

Old ledgers

The program does not rewrite a ledger. Check lines written up to step three
carry an English detail field and the verdict spelled with spaces. The program
still reads them as JSON records; it does not use check lines to propose, adopt
or check. New check lines hold the closed statement only.

A log the program cannot read in full is LEDGER-UNREADABLE (exit 6): a blank
line, a handwritten line that is not JSON, or a record without the fields
listed above. The program says which line, records nothing, repairs nothing,
and gives no verdict, also when a valid adoption stands earlier in the same
log. The log is read after the question is formed and asked of its files, so an
operation that stops earlier (an F1 to F4 or F8 refusal, NOT-RUN,
NOT-RECORDED) does not report on the log.

Paths to recording a non-question, found and closed

Step two. Step one wrote a check line for every check outcome, NOT CHECKED included.
With F8 that left a path: write a proposal line and an adoption line for a
non-question by hand (with a real signature made outside the program), then run
check with the wrong file or no file. The program cannot see that the question
is a non-question without its bytes, and it would have recorded a check line
for it. Since step two NOT CHECKED is reported and not recorded. A check line
is written only when the named bytes were presented, the question could be
asked of them, and a count was made. The cost: the log does not show attempts
where the bytes were not presented.

For the same reason NOT CHECKED does not by itself say that the question can be
asked. adopt saw that when it recorded the adoption, but check cannot tell an
adoption line this program wrote from one written by hand.

Step three. A form that names two files would open three paths if the second
file were handled loosely. Each is closed in ask, the one function propose,
adopt and check all call before anything is recorded:

- Fewer files than table lines (a share-agrees measure with one file). The number of files must equal the number of
  table lines, or the operation stops before any file is read. A question is
  never judged on some of its files.
- F8 on the first file only. F8 is applied to every named file.
- The files in either order. Each file is compared with the hash on its own
  table line, so the opposite order is "not presented".

Step four. Reading the given files again, we found no further path to recording
a non-question. ask is unchanged in what it decides and is still called first
by all three operations. What we found was in the answer side and is described
above: a crash exiting with a verdict's code, success of propose and adopt
exiting with the code of HOLDS, and a missing adopters file reported as a
signature that did not verify. All three are closed in this step.

After this step we know of no way, by calling propose, adopt or check from the
command line or from Python, to record a proposal, an adoption or a check of a
question that cannot be asked of its named bytes, in either form, including
with a handwritten proposal plus a valid signature. That is a statement about
the paths we read and closed, not a proof. We call the language closed, and
mean only this: every recorded question is well-formed and can be asked of its
named bytes; whether it is a good question is not decided here. The three
commands treat every caller the same. It is not a claim about the ledger.

What a verified signature does and does not show

It shows that ssh-keygen verified a signature over the measure bytes with a key
listed in your adopters file, checked again at every check against that file as
it is then. It does not show that a person held the key. If a tool is given a
listed key, this program cannot tell. A verifying signature does not make a
non-question adoptable (rule F8). Nothing stops a person signing a non-question
with ssh-keygen outside the program; that signature does not become an adoption
through adopt, and check refuses the question when its bytes are presented.
Outcome statements are not signed by anyone.

Step five: foundations

What it adds. A foundation is a signed name, plus up to three foundations it rests
on. A tag is a signed claim that a table (by its sha256) rests on a foundation. An
undermine is a signed statement that one foundation is knocked down, with an
adopted share-agrees measure as witness. impact lists everything that rests on a
foundation. check flags any verdict whose named tables rest, however far down, on a
knocked-down foundation. No question form, predicate or verdict rule changes.

What a foundation and a tag are, honestly. They are explicit signed commitments,
just like adopted measures. Only a holder of a listed key makes one (the program
cannot tell who). The program does not and cannot check that a tag is true of the
table: that the Earth table was in fact seen from Earth is the signer's claim. The
names are tokens; the program does not read them.

The texts (ASCII, one newline after every line, nothing else):

    reality 1                         reality 1                     reality 1
    foundation NAME                   tag                           undermine
    [rests-on sha256 FID]  (0 to 3,   table sha256 TABLE            foundation sha256 FID
     ascending, no repeats)           rests-on sha256 FID           witness sha256 MEASURE-ID

NAME is one run of printable ASCII bytes without spaces. Any other text is refused
under F9 (foundation, tag) or F10 (undermine), with a condition naming the line.
Step five's conditions: bad-line-count, not-a-foundation-line, not-a-rests-on-line,
rests-on-not-ascending, not-a-tag-line, not-a-table-line-of-tag, parent-not-adopted,
foundation-not-adopted, not-an-undermine-line, not-a-witness-line, other-witness,
not-a-comparison, witness-not-presented, witness-holds, not-a-side, both-sides,
foundation-file-unreadable, tag-file-unreadable, undermine-file-unreadable, and
bad-hash (NOT-RUN: impact was given something that is not 64 lowercase hex digits).

Namespaces. Foundations and tags are signed under reality-foundation-1, undermines
under reality-undermine-1, measures (unchanged) under reality-adopt-1. A signature
made under one namespace does not verify under another.

Operations.

    adopt-foundation LEDGER FOUNDATION SIG ADOPTER    -> ADOPTED foundation=FID adoption-line=N
    tag LEDGER TAG SIG ADOPTER                        -> ADOPTED foundation=FID tag=TID adoption-line=N
    undermine LEDGER UNDERMINE SIG ADOPTER WITNESS TABLE-1 TABLE-2
                                                      -> UNDERMINED foundation=FID side=S measure=MID
                                                         matching-1 rows-1 matching-2 rows-2 undermine-line=N
    impact LEDGER FID                                 -> IMPACT foundation=FID undermined=yes|no foundations=N
                                                         measures=M, then one DEPENDS line per dependent

There is no propose step for foundations or tags; adoption is the only step.

- adopt-foundation refuses (F9 parent-not-adopted) unless every rests-on foundation
  is already adopted. A foundation's id is the hash of its text, which names its
  parents' ids, and a parent must be adopted first; so the rests-on graph has no
  cycle. When the log is read, a foundation-adoption line counts only if its
  parents counted on earlier lines, so a handwritten line cannot make one either.
- tag refuses (F9 foundation-not-adopted) unless the foundation is adopted. It
  does not need the table's bytes, so a table can be tagged before it exists.
- undermine goes ahead only if all of these hold, in this order, and records
  nothing otherwise: the undermine text is well-formed (F10); the WITNESS file is
  the measure the text names (F10 other-witness) and is a share-agrees measure
  (F10 not-a-comparison); the foundation is adopted (F9); the witness has a
  verified adoption (F6, the same conditions as check); the two table files are
  the named bytes (F10 witness-not-presented, with file tokens); the witness,
  recounted now, is DOES-NOT-HOLD (F10 witness-holds, with the counts); the
  foundation is tagged, directly, on exactly one of the witness's two tables
  (F10 not-a-side, or both-sides); and the signature verifies under
  reality-undermine-1 (F5 not-verified). side= says which table it tags.
- The program records which side the signer named. It does not decide which side
  is wrong. A comparison that does not hold says the two shares differ, nothing
  more; the same witness would let a key holder name the other side instead.
- check: if any knocked-down foundation is under a named table (the table's tags,
  and everything those foundations rest on), HOLDS becomes HOLDS-UNDERMINED (exit
  12) and DOES-NOT-HOLD stays DOES-NOT-HOLD (exit 1); both carry
  undermined-foundation= and undermines=. The counts are unchanged. This applies to
  share-at-least and share-agrees alike.
- impact lists, in log order, adopted foundations that rest on FID however far
  down, then adopted measures (signature verified now) with a table tagged on FID
  or on one of those foundations.

What is re-verified, and what is not. Every time the log is read for a graph, each
foundation, tag and undermine line's signature is verified again, and an
undermine line counts only if its witness has a verified adoption and its
foundation is tagged on exactly one side. The recount of the witness happens when
undermine runs; it is not repeated on later reads, because the tables are not
given then. Running undermine again with the same files recounts it again (and
records another line). A holder of a listed key could write an undermine line
directly into the log, skipping the recount; check would count it.

What the log does not protect. Nothing changes from step four: the log is a plain
file. Anyone who can write it can delete, reorder or add lines, and the program
does not notice; deleting an undermine line silently un-flags everything under it
(there is a test that shows this). There is no hash chain, and no claim of
tamper-evidence for any line. Signed lines cannot be forged without a listed key,
but they can be removed. Check lines are unsigned records, not evidence.

Limits

- The log is a plain file and is not protected. A deleted line is gone, and the
  program does not detect that. Lines can be written directly, by hand or by
  code that calls record; that is writing the ledger, not proposing, adopting
  or checking. A ledger kept under step one may already hold an adoption of a
  non-question or a NOT CHECKED line; the program does not rewrite it.
- An adoption line written by hand with a verifying signature, for a question
  that can be asked of its bytes, counts as an adoption for check. check does
  not look for a proposal line.
- An adoption line whose measure was edited fails verification and is refused.
  Check lines are unsigned records of what the program computed.
- adoption-line is a line number in the log as it was when the statement was
  made. If lines are later removed or inserted, the number points elsewhere.
- The program only requires that it can read the adopters file. What the lines
  mean is left to ssh-keygen; a malformed adopters file shows as a signature
  that did not verify (F5 or F6).
- FAILED does not say what failed, and the program prints no traceback. A log
  line that has the needed fields but still cannot be used ends as FAILED or as
  a refusal, not as a verdict.
- If a check is made and recorded and the statement then cannot be printed (the
  output was closed, is full, or is a pipe whose reader has gone), the exit
  code is 10 (NOT-DELIVERED), nothing is written to standard error, and the
  check line stays in the log. For propose and adopt the code is 7 (FAILED),
  although adopt has then recorded its adoption line and propose may have
  recorded its proposal. If the output fails in a way the program cannot see
  (the write succeeds and the reader then loses it), the code is the verdict's.
- Two runs of the program on one ledger at the same time are not ordered. Each
  line is appended whole, but adoption-line is counted before the append, so it
  can point at the other run's line.
- A table file, log or adopters file that never ends (a pipe, or a device such
  as /dev/zero) is read until it ends or memory runs out. The program does not
  stop it. A MemoryError inside Python ends as FAILED; a process killed by the
  operating system prints no statement, and its status is not the program's.
- From Python, the five functions turn ordinary exceptions into Stop. They do
  not catch a keyboard interrupt, and the original exception remains reachable
  from the Stop object by a debugger. main catches everything.
- "The named bytes" rests on sha256 from the standard library. Two different
  files with one sha256 would be one table to this program; we rely on that not
  happening.
- share-agrees compares two shares under one predicate. It says nothing about
  where either file came from, and nothing about the files beyond those two
  shares.
- The test key is a throwaway labeled REALITY-TEST-KEY-NOT-PATSAK; it is not
  the key of patsak127 or of anyone.

Trusted surface

To trust a verdict you need to trust: reality.py, 691 lines; the Python
standard library; and the OpenSSH ssh-keygen on the machine. test_reality.py
and this spec are not part of the trusted surface. One test compares the
line count above with the saved file. (The file given for step three was 326
lines.)

Tests

    python3 -m unittest -v test_reality

Tested with Python 3.13/3.14 and OpenSSH ssh-keygen on Linux and Windows; the
program needs 3.10 or newer. The tests generate
throwaway keys and sign with them in test code; reality.py never does either.
Every table in the tests is made up for the tests.

The demo

run_demo.py (and run-demo.sh) runs the program on two real public datasets:
NASA/JPL Horizons ephemerides for Mars and Jupiter (2024-25), and Mirzadeh
et al. (ICLR 2025, arXiv:2410.05229v1 Table 1) for 25 evaluated language
models across static GSM8K (100) and GSM-Symbolic-NoOp. The hashes in the demo
are of our TSV conversions made by convert.py; SOURCES.md names every source
file and its sha256. The demo's "reads as", "means" and "(exit N)" lines are
printed by the demo script, not by reality.py. Adoptions there are signed with
a throwaway test key.

Not in this step

No third question form, no second predicate, no new table format, no bar on the
agreement form, no word "same" in the language. No statement about where bytes
came from. No reading of English. No judgement of measures. No protection of
the ledger files, and no ledger hashing or chaining. No signing of outcomes and
no signing or re-adopting by the program. No verbose or fallback free-text
mode. No echoing of input text other than hashes, counts and closed tokens. No
accepting of outcome statements as inputs. No addition to the trusted base. No
wording stronger than: the program emits only statements from a closed, listed
form.
