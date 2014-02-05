# Simple makefile for building and testing BORIS app bundles

default:
	pyinstaller BORIS.spec
	cp Info.plist dist/BORIS.app/Contents/

clean:
	rm -rf dist build

test:
	open dist/BORIS.app
