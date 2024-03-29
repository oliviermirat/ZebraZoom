# Releasing new versions
Go to Actions, select 'Release a new version' workflow, click on Run workflow, enter the release version and run it.

# Running tests
Short tests are run automatically on every push. To run long tests on Github, go to Actions, select 'Long running automated tests' workflow and run it using the desired branch. When running tests, temporary folders are used instead of standard zebrazoom data folders, so tests won't interfere with the existing local data and won't leave any files behind.

To run tests locally, install the dependencies with `pip install pytest pytest-qt pytest-cov` and then run tests using `python -m pytest --long -s test/`. This command will run all tests; to skip long tests, simply omit the `--long` argument.

# Generating coverage report
Coverage report can be generated by specifying additional arguments when running tests, for example `python -m pytest --cov-report html --cov=zebrazoom --long -s test/`. To look at the generated report, open `index.html` in folder `htmlcov` using your browser.