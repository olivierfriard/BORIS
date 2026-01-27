
# list of recipes
default:
    just --list

# create a wheel with last version
build:
    rm -rf *.egg-info build dist
    # update version in pyproject.toml
    uv version $(grep '__version__' boris/version.py | awk -F'"' '{print $2}')
    git commit -am "new wheel" || true
    git push
    uv build

publish:
    # uvx twine upload --verbose --repository pypi dist/*
    uv publish

publish_test:
    uvx twine upload --verbose --repository testpypi dist/*
    # uv publish --index 




