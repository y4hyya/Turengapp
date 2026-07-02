# Tureng — build & install helpers
#
#   make run      - run from source (quick testing, no build)
#   make build    - build a fresh standalone Tureng.app into dist/
#   make install  - build, replace /Applications/Tureng.app, relaunch
#   make clean    - remove build artifacts (build/ and dist/)

APP  = Tureng.app
DEST = /Applications/$(APP)

.PHONY: run build install clean

run:
	python3 app.py

build: clean
	python3 setup.py py2app

install: build
	-pkill -x Tureng
	rm -rf $(DEST)
	ditto dist/$(APP) $(DEST)
	open $(DEST)
	@echo "✓ Installed and launched $(DEST)"

clean:
	rm -rf build dist
