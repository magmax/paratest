all: test

test: code_analysis test_unittest test_acceptance

test_unittest:
	py.test tests/unit tests/integration

test_acceptance:
	py.test tests/acceptance -p no:cov

code_analysis:
	flake8 paratest tests --stat --count
