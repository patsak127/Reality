# NARPS team IZ20, hypotheses 7-9 (amygdala, positive effect of loss).
# Decisions (results.tsv): H7 (EI) = Yes, H8 (ER) = No, H9 (ER > EI) = No.
use si
dimension Money
kind Loss : Money
entity Participant
entity Template
artifact parts = file "participants.tsv" sha256 "d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8"
artifact results = file "results.tsv" sha256 "90f8b31898e3f576fd7c8c5333bf543faf881a228541b24b6f35646444a17531"
artifact templates = file "templates.tsv" sha256 "428d2c083efa9c8af62e839e84bd0c561f9447467322fbba57ceb674d89f083b"
artifact pipelines_xlsx = ref sha256 "e00984c14e3c21a1f950e52756aba4c6a33102a176eae80e6049d235f6ec1c3f"
procedure spm_rft from pipelines_xlsx
procedure fdr_voxelwise from pipelines_xlsx
note "IZ20 excluded no one (n_participants 108)."
group EI of Participant { members: parts rows where "group" is "equalIndifference", key: "participant_id" }
group ER of Participant { members: parts rows where "group" is "equalRange", key: "participant_id" }
effect loss_positive { variable: Loss, modulation: parametric, direction: positive }
individual spm_mni : Template from templates cell "template" where "team" is "IZ20"
note "region_definition_amygdala (organisers' coding): 'atlas AFNI embeded atlases'. Not in the release as a table."
region amygdala_IZ20 { atlas: pipelines_xlsx rows where "teamID" is "IZ20", space: spm_mni }

# H9 as recorded. The team's statistic_type text says SPM voxel-wise FWE p<0.05; the organisers'
# coded columns say FDR voxelwise, p<0.05. The team's maps are t values; no degrees of freedom are given.
test t_IZ20_H9 {
  compares: ER > EI
  design: independent
  effect: loss_positive
  region: amygdala_IZ20
  search: whole_brain
  statistic: t
  sign: positive_means ER > EI
  correction: fwe(alpha: 0.05, method: spm_rft)
  correction: fdr(q: 0.05, method: fdr_voxelwise)
}
result r_IZ20_H9 = not_significant(t_IZ20_H9) from results cell "decision" where "result" is "IZ20/H9"

# The same test, keeping only the team's own words for the correction.
test t_IZ20_H9_team_text {
  compares: ER > EI
  design: independent
  effect: loss_positive
  region: amygdala_IZ20
  search: whole_brain
  statistic: t
  sign: positive_means ER > EI
  correction: fwe(alpha: 0.05, method: spm_rft)
}

# What IZ20's H7 = Yes and H8 = No suggest when read together.
claim D78 = differs(loss_positive in amygdala_IZ20: EI > ER)
