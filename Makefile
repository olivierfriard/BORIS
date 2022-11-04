create_wheel:
	git commit -am "new wheel"; git push; rm -rf *.egg-info build dist; python3 setup.py sdist bdist_wheel; twine check dist/*


upload_pip_test:
	python3 -m twine upload --repository testpypi dist/*


upload_pip:
	python3 -m twine upload dist/*




