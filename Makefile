
VENV ?= ./venv

# Dependencies
venv:
	test -d $(VENV) || virtualenv $(VENV)

dep-gobal:
	test -d ./dist || mkdir -p ./dist |true

dep-dev: dep-deploy

dep-build: dep-deploy

dep-deploy: venv dep-gobal
	$(VENV)/bin/pip install -r requirements-build.txt  >/dev/null

# Build
build: clean dep-build
	@echo "#> Building package on ./dist/ dir"
	$(VENV)/bin/python setup.py sdist bdist_wheel
	@echo "#> Done. Packages on ./dist/"
	@ls ./dist

# Test (TODO)
# test-dev:
# 	$(VENV)/bin/twine check dist/*

# Bump version
bump: clean dep-dev
	$(VENV)/bin/bumpversion --current-version `git tag |tail -n1` \
		$(BUMP_LEVEL) ./glpi/version.py

bump-major:
	$(MAKE) bump BUMP_LEVEL=major

bump-minor:
	$(MAKE) bump BUMP_LEVEL=minor

bump-patch:
	$(MAKE) bump BUMP_LEVEL=patch

# Tag
REPO_BRANCH ?= `git branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/\1/'`
REPO_VERSION ?= `sed "s/__version__ \= //g" glpi/version.py |tr -d "'"`
tag:
	@if [ "$(REPO_BRANCH)" != "master" ]; then \
		echo "#>> ERR - Your should have in the master branch to create tag."; \
		echo "#>> Current branch: $(REPO_BRANCH)"; \
		exit 1; \
	fi
	git tag $(REPO_VERSION) -m "Bump to $(REPO_VERSION) by Makefile" && \
		git push --tags origin

# Deploy
deploy-test: build
	#$(VENV)/bin/twine check dist/*	 #TODO fix: is not working
	$(VENV)/bin/twine upload \
		-u $(TWINE_USERNAME) \
		-p $(TWINE_PASSWORD) \
		--repository-url https://test.pypi.org/legacy/ \
		--verbose \
		dist/*

deploy-prod: build
	$(VENV)/bin/twine upload \
		-u $(TWINE_USERNAME) \
		-p $(TWINE_PASSWORD) \
		--verbose \
		dist/*

# Clean artifacts
clean:
	@echo "#> Cleaning project's artifacts"
	@rm -rf disk/*

clean-venv:
	@rm -rf $(VENV)
