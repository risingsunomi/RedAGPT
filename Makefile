SHELL :=./make-venv
SHELL := /bin/sh

.DEFAULT_GOAL := help

VENV := .venv
PYTHON := python3.8


virtualenv: ## Create virtualenv
	@if [ -d ${VENV} ]; then rm -rf ${VENV}; fi
	@mkdir ${VENV}
	${PYTHON} -m venv ${VENV}
	${VENV}/bin/pip install --upgrade pip==23.2.1
	${VENV}/bin/pip install -r requirements.txt

update-requirements-txt: VENV := /tmp/venv/
update-requirements-txt: ## Update requirements.txt
	@if [ -d ${VENV} ]; then rm -rf ${VENV}; fi
	@mkdir ${VENV}
	${PYTHON} -m venv ${VENV}
	${VENV}/bin/pip install --upgrade pip==23.2.1
	${VENV}/bin/pip install -r unpinned_requirements.txt
	echo "# Created automatically by make update-requirements-txt. Do not update manually!" > requirements.txt
	${VENV}/bin/pip freeze | grep -v pkg_resources >> requirements.txt

clean: ## Clean python cache
	find . -type d -name "__pycache__" -exec rm -rf {} \;

help: ## Show help message
	@IFS=$$'\n' ; \
	help_lines=(`fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##/:/'`); \
	printf "%s\n\n" "Usage: make [task]"; \
	printf "%-24s %s\n" "task" "help" ; \
	printf "%-24s %s\n" "------" "----" ; \
	for help_line in $${help_lines[@]}; do \
		IFS=$$':' ; \
		help_split=($$help_line) ; \
		help_command=`echo $${help_split[0]} | sed -e 's/^ *//' -e 's/ *$$//'` ; \
		help_info=`echo $${help_split[2]} | sed -e 's/^ *//' -e 's/ *$$//'` ; \
		printf '\033[36m'; \
		printf "%-24s %s" $$help_command ; \
		printf '\033[0m'; \
		printf "%s\n" $$help_info; \
	done

.PHONY: help clean update-requirements-txt virtualenv
