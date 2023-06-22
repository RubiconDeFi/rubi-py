import os
import sys

def test(args=sys.argv):
    os.chdir("tests")
    if(len(args) > 1):
        selector_flag = args[1]
        test_name = args[2]
        os.system(f"pytest rubi_tests.py -v {selector_flag} {test_name}")
    else:
        os.system("pytest rubi_tests.py -v")

def test_with_coverage():
    os.chdir("tests")
    os.system("coverage run -m pytest -v rubi_tests.py && coverage report -m")

def test_coverage_html():
    os.chdir("tests")
    os.system("coverage run -m pytest -v rubi_tests.py && coverage html && open htmlcov/index.html") 