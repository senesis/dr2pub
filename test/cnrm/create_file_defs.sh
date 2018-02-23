#!/bin/bash
#set -x
#
# Create XIOS file_defs for each context described in file in arg3 ,
# for the simulation described by file in arg4
# and accounting for a few other args
#
# Assumes that a full set of xml files is available in current dir,
# including ping_files (named like ping_<context>*.xml)
#
# Output files are named after pattern dr2xml_<context>.xml
#
dummies=$1 ; shift # See dr2xml doc : forbid/skip/include
EXPID=$1 ; shift # The value for an attribute 'EXPID' in datafiles
ln -sf $1 lab_and_model_settings_tmp.py ; shift
ln -sf $1 simulation_settings_tmp.py ; shift
year=$1 ; shift # year that will be simulated
enddate=$1 ; shift  # simulation end date - YYYYMMDD - must be at 00h next day
ncdir=${1:-@IOXDIR@/} ; shift  # Directory for data outpu files
print=${1:-1} ; shift # Want some reporting ?
homedr=$1 ; shift # Filename for a 'home' data request - optional
path_extra_tables=$1 # Filename for a 'home' data request - optional
#dummies=include
#
# Set paths for all software components
#
root=$(cd $(dirname $0) ; pwd)
cvspath=$root/CMIP6_CVs # Path for CMIP6_CV
dr2xmlpath=${altdr2xmlpath:-$root/dr2pub}
DRpath=$root/01.00.21/dreqPy
#
CVtag=cv=$(cd $cvspath ; git describe HEAD ) 
export PYTHONPATH=$dr2xmlpath:$DRpath:$PYTHONPATH
#
# Identify which ping_files are used (according to $(pwd)/iodef.xml)
#
pings=$(grep "ping_.*\.xml" iodef.xml | grep -v "<!--" | sed -r -e 's/.*(ping_.*xml).*/\1/g' | tr "\n" " ")
#
# Create Python script for using dr2xml's generate_file_defs()
#
cat >create_file_defs.tmp.py  <<-EOF
	#!/usr/bin/python
	from lab_and_model_settings_tmp import lab_and_model_settings
	from simulation_settings_tmp import simulation_settings
	from dr2xml import generate_file_defs
	import sys, os, traceback
	#print "* CMIP6_CV commit : "
	#os.system("cd $cvspath ; git log --oneline | head -n 1 | cut -d\  -f 1")
	#print
	#
	if $print=="1" : printout=True
	else : printout=False
	#
	if "$homedr" : 
	  simulation_settings['listof_home_vars']="$homedr"
	if "$path_extra_tables" : 
	  simulation_settings['path_extra_tables']="$path_extra_tables" 
	config=simulation_settings['configuration']
	configuration_triplet=lab_and_model_settings['configurations'][config]
	config_unused=configuration_triplet[2]
	exp_unused=simulation_settings.get('unused_contexts',[])
	#print "exp_unsued=",exp_unused," config_unused=",config_unused
	contexts=[ c for c in lab_and_model_settings['realms_per_context'] \
	  if c not in exp_unused and c not in config_unused ]
	for context in contexts :
	    ok=generate_file_defs(lab_and_model_settings,
	                       simulation_settings,
	                       year       =$year,
	                       enddate    ="$enddate",
	                       context    =context,
	                       pingfiles  ="$pings",
	                       printout   =$print, 
	                       cvs_path   ="${cvspath}/",
	                       dummies    ="$dummies",
	                       dirname    ="./",
	                       prefix     ="$ncdir",
                               attributes =[ ("EXPID","$EXPID") , ("CMIP6_CV_version", "$CVtag") ]
                               )
	#if not ok : sys.exit(1)
	EOF


[[ $(uname -n) == beaufix* ]] && module load python/2.7.5-2 2>/dev/null
[[ $(uname -n) == prolix*  ]] && module load python/2.7.5   2>/dev/null
python create_file_defs.tmp.py
ret=$?
rm create_file_defs.tmp.py simulation_settings_tmp.py lab_and_model_settings_tmp.py
exit $ret
