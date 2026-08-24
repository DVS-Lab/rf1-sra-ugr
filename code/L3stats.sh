#!/bin/bash

# This script will perform Level 3 statistics in FSL.
# Rather than having multiple scripts, we are merging three analyses
# into this one script:
#		1) two groups (older vs. younger)
#		2) two groups (older vs. younger), with covariates
#		3) single group average
#
# This script can also run randomise (permutation-based stats) on existing output.
# By default, randomise will not be be run if FEAT analyses do not exist. In addition,
# randomise will only be run on copes above a specified number (see copenum_thresh_randomise variable).
# If you have no intention of running randomise, you set copenum_thresh_randomise=20 (> max of 19 copes)
# and you could uncomment out the rm lines that remove the filtered_func_data file (save disk space).

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"

# study-specific inputs and general output folder

copenum=$1
copename=$2
analysis=$3
REPLACEME=act # act  ppi, nppi # this defines the parts of the path that differ across analyses
type=${REPLACEME} # For output template

# Variables that change per analysis. Check carefully! 
covariate=ones

N=304 # update with total n after exclusions

if [[ $analysis == "act" ]]; then
	template=L3_task-ugr_model-3_type-act_group-${covariate}_n${N}_flame1.fsf 
else
	template=L3_task-ugr_model-3_type-ppi_group-${covariate}_n${N}_flame1.fsf
fi


# Set once and then forget.
model=3 # or model 2
task=ugr
modeltype=flame1
templatedir="/ZPOOL/data/projects/rf1-sra-ugr/templates"
#MAINOUTPUT=${maindir}/derivatives/fsl/L3-act/L3_model-${model}_task-${task}_type-${type}-n${N}-cov-${covariate}-${modeltype}
MAINOUTPUT=${maindir}/derivatives/fsl/L3-act/L3_model-${model}_task-${task}_type-${type}-n${N}-cov-${covariate}-${modeltype}

mkdir -p $MAINOUTPUT

# set outputs and check for existing
cnum_pad=`zeropad ${copenum} 2`
OUTPUT=${MAINOUTPUT}/L3_model-${model}_task-${task}_n${N}-cov-${covariate}-cope-${copenum}_cname-${copename}-${modeltype}

	echo "[$(date)] re-doing: ${OUTPUT}" >> re-runL3.log
	rm -rf ${OUTPUT}.gfeat

	# create template and run FEAT analyses
	ITEMPLATE=${templatedir}/${template}
	OTEMPLATE=${MAINOUTPUT}/L3_task-${task}_model-${model}_type-${type}_cope-${copenum}_cname-${copename}_${covariate}_n${N}_${modeltype}.fsf
	sed -e 's@OUTPUT@'$OUTPUT'@g' \
	-e 's@COPENUM@'$copenum'@g' \
	-e 's@REPLACEME@'$REPLACEME'@g' \
	-e 's@BASEDIR@'$maindir'@g' \
	<$ITEMPLATE> $OTEMPLATE
	/usr/local/fsl/bin/feat $OTEMPLATE
	# feat $OTEMPLATE

# delete unused files
 rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/stats/res4d.nii.gz
 rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/stats/corrections.nii.gz
 rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/stats/threshac1.nii.gz
#rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/filtered_func_data.nii.gz
# rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/var_filtered_func_data.nii.gz
