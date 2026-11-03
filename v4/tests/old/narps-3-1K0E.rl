# NARPS team 1K0E, hypotheses 7-9 (amygdala, positive effect of loss).
# Decisions (results.tsv): H7 (EI) = No, H8 (ER) = Yes, H9 (ER > EI) = Yes.
# Read together, H7 and H8 suggest "the effect is larger in ER than in EI". Unlike the
# 08MQ pair, this difference has a test: hypothesis 9 compares the groups.
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
procedure palm_fwe from pipelines_xlsx
note "1K0E excluded 19 participants on MRIQC motion criteria (exclusions_details); the members below are 48 and 41."
group EI of Participant { members: parts rows where "group" is "equalIndifference" minus excl rows where "team" is "1K0E", key: "participant_id" }
group ER of Participant { members: parts rows where "group" is "equalRange" minus excl rows where "team" is "1K0E", key: "participant_id" }
effect loss_positive { variable: Loss, modulation: parametric, direction: positive }
individual hcp : Template from templates cell "template" where "team" is "1K0E"
note "region_definition_amygdala (organisers' coding): 'atlas HCP'. Not in the release as a table."
region amygdala_1K0E { atlas: pipelines_xlsx rows where "teamID" is "1K0E", space: hcp }
note "statistic_type: TFCE; pval_computation: 2000 permutations; multiple_testing_correction: FWE in PALM, alpha 0.05 (the 0.05 in its Sidak formula)."
test t_1K0E_H9 {
  compares: ER > EI
  design: independent
  effect: loss_positive
  region: amygdala_1K0E
  search: whole_brain
  statistic: tfce(permutations: 2000)
  sign: positive_means ER > EI
  correction: fwe(alpha: 0.05, method: palm_fwe)
}
result r_1K0E_H9 = significant(t_1K0E_H9) from results cell "decision" where "result" is "1K0E/H9"

claim D78 = differs(loss_positive in amygdala_1K0E: ER > EI) by r_1K0E_H9
