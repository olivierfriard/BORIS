
# create a wheel with last version
build:
    rm -rf *.egg-info build dist
    sed -i "/^version = /c\version = \"$(grep '__version__' boris/version.py | awk -F'"' '{print $2}')\"" pyproject.toml
    sed -i "/^current_version = /c\current_version = \"$(grep '__version__' boris/version.py | awk -F'"' '{print $2}')\"" pyproject.toml
    git commit -am "new wheel" || true
    git push
    uv build

publish:
    uvx twine upload --verbose --repository pypi dist/*

publish_test:
    uvx twine upload --verbose --repository testpypi dist/*




