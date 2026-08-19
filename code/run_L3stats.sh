#!/bin/bash

# This run_* script is a wrapper for L3stats.sh, so it will loop over several
# copes and models. Note that Contrast N for PPI is always PHYS in these models.


# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"


# Change the type of analysis in the " " marks.

for analysis in "act"; do # "act" "ppi_seed-pTPJ"

	# Define the contrast value and the name you would like in the output. 

	analysistype=${analysis}		
		for copeinfo in "11 offer-unfairness_pmod" "12 social-nonsocial_pmod"; do
		# for copeinfo in "1 nonsocial_high_c" "2 nonsocial_high_pmod" "3 nonsocial_low_c" "4 nonsocial_low_pmod" "5 social_high_c" "6 social_high_pmod" "7 social_low_c" "8 social_low_pmod" "9 endowment_high-low_c" "10 social-nonsocial_c" "11 offer-unfairness_pmod" "12 social-nonsocial_pmod" "13 nonsocial_pmod" "14 social_pmod" "15 endowment_high-low_pmod" "16 nonsocial_high-low_pmod" "17 social_high-low_pmod" "18 phys"; do
# split copeinfo variable
		set -- $copeinfo
		copenum=$1
		copename=$2

		NCORES=25
		SCRIPTNAME=${maindir}/code/L3stats.sh
		echo $SCRIPTNAME
		while [ $(ps -ef | grep -v grep | grep $SCRIPTNAME | wc -l) -ge $NCORES ]; do
			sleep 1s
		done
		bash $SCRIPTNAME $copenum $copename $analysistype &
		echo "$SCRIPTNAME $copenum $copename $analysistype"

	done
done
