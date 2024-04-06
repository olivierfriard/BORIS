

# create a wheel with last version
build:
    sed -i "/^version = /c\version = \"$(grep '__version__' boris/version.py | awk -F'"' '{print $2}')\"" pyproject.toml
    sed -i "/^current_version = /c\current_version = \"$(grep '__version__' boris/version.py | awk -F'"' '{print $2}')\"" pyproject.toml
    #dtf pyproject.toml   # dtf (dynamic text file required on path)
    git commit -am "new wheel"
    git push
    rye build --clean

publish:
    rye publish

publish_test:
    rye publish --repository testpypi --repository-url https://test.pypi.org/legacy/



create_wheel:
	dtf pyproject.toml   # dtf (dynamic text file required on path)
	git commit -am "new wheel"; git push; rm -rf *.egg-info build dist
	python3 -m build
	twine check dist/*

# upload wheel on testPyPI
upload_pip_test:
	python3 -m twine upload --verbose --repository testpypi dist/*

# upload wheel on PyPI
upload_pip:
	python3 -m twine upload --verbose dist/*




