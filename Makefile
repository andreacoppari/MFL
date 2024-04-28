exe:
	@pyinstaller --onefile -n MFL main.py
install:
	@pip install -r requirents

default: install

.PHONY: install exe