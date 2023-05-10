

# export x=$(grep '__version__' boris/version.py | awk -F'"' '{print $2}')
# sed "s|###VERSION###|${x}|g" pyproject_template.toml > pyproject.toml


create_wheel:
	rst_exe pyproject.toml
	git commit -am "new wheel"; git push; rm -rf *.egg-info build dist
	python3 -m build
	twine check dist/*


upload_pip_test:
	python3 -m twine upload --verbose --repository testpypi dist/*


upload_pip:
	python3 -m twine upload --verbose dist/*




