VENV := .venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip
LAB := $(VENV)/bin/harmonium-lab
REFS_DIR := references
GENERATED_DIR := ../harmonium/harmonium_core/target/generated_music
REPORTS_DIR := target/quality_reports

.PHONY: setup corpus profiles test lab-export suite gate clean help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ════════════════════════════════════════════════════════════════════
# SETUP
# ════════════════════════════════════════════════════════════════════

setup: $(VENV)/bin/activate ## Create venv and install harmonium_lab
$(VENV)/bin/activate:
	python3 -m venv $(VENV)
	$(PIP) install -e ".[dev]"

# ════════════════════════════════════════════════════════════════════
# REFERENCE CORPUS
# ════════════════════════════════════════════════════════════════════

corpus: ## Download reference MIDI corpus (28 files, 5 categories)
	bash scripts/download_corpus.sh

profiles: setup ## Build reference profiles from corpus MIDI files
	@for cat in ambient jazz-calm jazz-upbeat training-backing classical-simple; do \
		echo "Building profile: $$cat..."; \
		$(LAB) profile \
			--input "$(REFS_DIR)/$$cat" \
			--category "$$cat" \
			--output "$(REFS_DIR)/$$cat/profile.json"; \
	done
	@echo "All profiles built."

# ════════════════════════════════════════════════════════════════════
# ANALYSIS
# ════════════════════════════════════════════════════════════════════

lab-export: ## Generate MIDI+JSON from harmonium (runs Rust tests)
	cd ../harmonium && $(MAKE) test/lab-export

suite: setup ## Run full analysis suite on generated music
	@mkdir -p $(REPORTS_DIR)
	$(LAB) suite \
		-i $(GENERATED_DIR) \
		-o $(REPORTS_DIR) \
		$(if $(PROFILE),--profile $(PROFILE),)

gate: ## Run quality gate on latest reports (REPORT=path required)
	$(LAB) gate \
		--report $(REPORT) \
		$(if $(BASELINE),--baseline $(BASELINE),) \
		$(if $(MIN_COMPOSITE),--min-composite $(MIN_COMPOSITE),)

# ════════════════════════════════════════════════════════════════════
# FULL PIPELINE
# ════════════════════════════════════════════════════════════════════

pipeline: lab-export suite ## Full pipeline: generate music → analyze → report
	@echo ""
	@echo "Pipeline complete. Reports in $(REPORTS_DIR)/"

# ════════════════════════════════════════════════════════════════════
# TESTING
# ════════════════════════════════════════════════════════════════════

test: setup ## Run all Python tests
	$(VENV)/bin/pytest tests/ -v

# ════════════════════════════════════════════════════════════════════
# CLEANUP
# ════════════════════════════════════════════════════════════════════

clean: ## Remove generated reports and profiles
	rm -rf $(REPORTS_DIR)
	rm -f $(REFS_DIR)/*/profile.json

clean-all: clean ## Remove venv and all generated files
	rm -rf $(VENV) .pytest_cache __pycache__ src/harmonium_lab/__pycache__
