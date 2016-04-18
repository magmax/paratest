all: test

test: code_analysis test_unit test_acceptance

test_unit:
	py.test tests/unit tests/integration --cov-report=term-missing --cov paratest

test_acceptance:
	py.test tests/acceptance -p no:cov

code_analysis:
	flake8 paratest tests --stat --count
