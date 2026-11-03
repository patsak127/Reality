# NARPS team 08MQ, hypotheses 5 and 6 (vmPFC, negative effect of loss), from the team's own records.
# Decisions (results.tsv, from narps_results.xlsx): H5 (EI) = Yes; H6 (ER) = No.
# The tables beside this file are read and checked against their SHA-256; extract.py says where each came from.
use si
dimension Money
kind Loss : Money
entity Participant
entity Template
artifact parts = file "participants.tsv" sha256 "d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8"
artifact excl = file "exclusions.tsv" sha256 "53d3c740f7933e6ea8e12bd24a33daf1a1a1ae8812226316e89fc06af7236664"
artifact results = file "results.tsv" sha256 "90f8b31898e3f576fd7c8c5333bf543faf881a228541b24b6f35646444a17531"
artifact templates = file "templates.tsv" sha256 "428d2c083efa9c8af62e839e84bd0c561f9447467322fbba57ceb674d89f083b"
artifact pipelines_xlsx = ref sha256 "e00984c14e3c21a1f950e52756aba4c6a33102a176eae80e6049d235f6ec1c3f"
procedure randomise_fwe from pipelines_xlsx
note "08MQ excluded sub-072 and sub-089 (exclusions_details); the members below are 53 and 53, as its text says."
group EI of Participant { members: parts rows where "group" is "equalIndifference" minus excl rows where "team" is "08MQ", key: "participant_id" }
group ER of Participant { members: parts rows where "group" is "equalRange" minus excl rows where "team" is "08MQ", key: "participant_id" }
effect loss_negative { variable: Loss, modulation: parametric, direction: negative }
individual mni_2mm : Template from templates cell "template" where "team" is "08MQ"
note "08MQ's mask (regions_definition): Harvard-Oxford cortical atlas (thr25), keeping voxels below MNI x 0, anterior of y 8, z -12 to 12. The mask is not in the release, so the region rests on the pipelines file, unread."
region vmPFC_08MQ { atlas: pipelines_xlsx rows where "teamID" is "08MQ", space: mni_2mm }

note "statistic_type: TFCE.; pval_computation: randomise, 10,000 permutations; multiple_testing_correction: 'FWE permutation (10,000 permutations).' No level is given."
test t_08MQ_H5 {
  compares: in EI for negative_effect
  effect: loss_negative
  region: vmPFC_08MQ
  search: whole_brain
  statistic: tfce(permutations: 10000)
  sign: positive_means negative_effect
  correction: fwe(method: randomise_fwe)
}
test t_08MQ_H6 {
  compares: in ER for negative_effect
  effect: loss_negative
  region: vmPFC_08MQ
  search: whole_brain
  statistic: tfce(permutations: 10000)
  sign: positive_means negative_effect
  correction: fwe(method: randomise_fwe)
}

# What the two decisions suggest when read together: "the negative loss effect in vmPFC is
# stronger in EI than in ER". No NARPS hypothesis tests this difference.
claim D56 = differs(loss_negative in vmPFC_08MQ: EI > ER)
