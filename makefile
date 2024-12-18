# Default year for the script
YEAR=2024

# Target to run the script
run:
	@echo "Running the team ranking script..."
	@python3 rankings.py $(YEAR) $(API_KEY)

