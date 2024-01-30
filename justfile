

# create a wheel with last version
create_wheel:
	rst_exe pyproject.toml
	git commit -am "new wheel"; git push; rm -rf *.egg-info build dist
	python3 -m build
	twine check dist/*

# upload wheel on testPyPI
upload_pip_test:
	python3 -m twine upload --verbose --repository testpypi dist/*

# upload wheel on PyPI
upload_pip:
	python3 -m twine upload --verbose dist/*




