# The pipelines table as released: 08MQ's teamID cell is "08MQ" followed by U+2002 (an en space).
# Selecting the row by "08MQ" would silently find nothing, or find it only if blanks were trimmed.
# Reality refuses to compare a column with a blank at the edge of a cell (W007).
use si
entity Team
artifact pipelines = file "pipelines.tsv" sha256 "27bc66041fa2375d24bd343e6e582edbdaa3aa4e133a218e35b9ced7f515a6e6"
individual team_08MQ : Team from pipelines rows where "teamID" is "08MQ"
