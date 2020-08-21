pkg_install := $(shell dnf -y install git rpm-build)
commit := $(shell git log --pretty=format:'%H' -n 1)
commit_date := $(shell git log --pretty='format:%cd' --date='format:%Y%m%d' -n 1)
short_commit := $(shell git rev-parse --short=9 HEAD)

srpm:
	if test ! -d SOURCES; then mkdir SOURCES; fi
	if test ! -d SPEC; then mkdir SPEC; fi
	git archive --prefix="avocado-$(commit)/" -o "SOURCES/avocado-$(short_commit).tar.gz" HEAD
	cp python-avocado.spec SPEC
	sed -i -e 's/\%global rel_build .*/\%global rel_build 0/' SPEC/python-avocado.spec
	sed -i -e 's/\%global commit .*/\%global commit $(commit)/' SPEC/python-avocado.spec
	sed -i -e 's/\%global commit_date .*/\%global commit_date $(commit_date)/' SPEC/python-avocado.spec
	rpmbuild -D '_topdir .' -bs SPEC/python-avocado.spec
	mv SRPMS/*.src.rpm $(outdir)
