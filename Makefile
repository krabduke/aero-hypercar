BLENDER := /Applications/Blender.app/Contents/MacOS/Blender
BLEND   := build/car.blend
SAMPLES ?= 128

.PHONY: all build verify render export stl manifest viewer validate aero clean

all: build verify render export manifest

build:
	$(BLENDER) --background --python car/assemble.py

verify:
	python3 car/verify.py

render:
	$(BLENDER) -b $(BLEND) -P car/render.py -- all $(SAMPLES)

export:
	$(BLENDER) -b $(BLEND) -P car/export.py -- glb

stl:
	$(BLENDER) -b $(BLEND) -P car/export.py -- stl

manifest:
	python3 tools/make_manifest.py

viewer:
	@echo "Serving http://localhost:8792/viewer/ - Ctrl-C to stop"
	@python3 -m http.server 8792 --bind 127.0.0.1

clean:
	rm -rf build renders

BPY := /Applications/Blender.app/Contents/Resources/5.2/python/bin/python3.13

validate:
	$(BPY) aero/validate.py

aero:
	$(BPY) aero/analyse.py
