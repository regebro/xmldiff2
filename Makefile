root_dir := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
dfm_source := "https://raw.githubusercontent.com/google/diff-match-patch/master/python2/diff_match_patch.py"

update-diff-match-patch:
	wget $(dfm_source)  -O $(root_dir)/xmldiff2/diff_match_patch.py

