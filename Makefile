

default:
	pyinstaller BORIS.spec

clean:
	rm -rf dist build

test:
	open dist/BORIS.app
