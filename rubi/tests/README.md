# rubi-py testing suite

This testing suite covers the rubi-py sdk's entire codebase. Our testing coverage is currently at 50%

## Installation and Setup:

To run the entire test suite, execute the following command in your terminal:

```shell 
    pytest rubi_tests.py
```

To run specific tests, you can use the -k flag followed by the name of the test. For example, to run tests related to
adding pairs, you can use:

```shell
    pytest rubi_tests.py -k add_pair
```

To view more detailed output during the test run, you can use the -v flag for a verbose mode:

```shell
    pytest rubi_tests.py -v
```

## Test coverage

To run and generate test coverage, and then view the report on coverage run:

```shell
    coverage run -m pytest -v rubi_tests.py && coverage report -m
```

To generate an html view of coverage run:

```shell
    coverage run -m pytest -v rubi_tests.py && coverage html && open htmlcov/index.html
```

### Coverage report


| Name                                                                |    Stmts |    Miss |   Cover |
|---------------------------------------------------------------------|---------:|--------:|--------:|
| rubi-py/rubi/rubi/\_\_init\_\_.py                                   |        4 |       0 |    100% |
| rubi-py/rubi/rubi/client.py                                         |      168 |      24 |     86% |
| rubi-py/rubi/rubi/contracts/\_\_init\_\_.py                         |        5 |       0 |    100% |
| rubi-py/rubi/rubi/contracts/base\_contract.py                       |       64 |       7 |     89% |
| rubi-py/rubi/rubi/contracts/contract\_types/\_\_init\_\_.py         |        2 |       0 |    100% |
| rubi-py/rubi/rubi/contracts/contract\_types/events.py               |      134 |      18 |     87% |
| rubi-py/rubi/rubi/contracts/contract\_types/transaction\_reciept.py |       25 |       2 |     92% |
| rubi-py/rubi/rubi/contracts/erc20.py                                |       63 |      14 |     78% |
| rubi-py/rubi/rubi/contracts/market.py                               |       60 |      12 |     80% |
| rubi-py/rubi/rubi/contracts/router.py                               |       35 |      11 |     69% |
| rubi-py/rubi/rubi/network/\_\_init\_\_.py                           |        1 |       0 |    100% |
| rubi-py/rubi/rubi/network/network.py                                |       69 |      28 |     59% |
| rubi-py/rubi/rubi/rubicon\_types/\_\_init\_\_.py                    |        3 |       0 |    100% |
| rubi-py/rubi/rubi/rubicon\_types/order.py                           |      121 |      21 |     83% |
| rubi-py/rubi/rubi/rubicon\_types/orderbook.py                       |       55 |      12 |     78% |
| rubi-py/rubi/rubi/rubicon\_types/pair.py                            |       19 |       1 |     95% |
| \_\_init\_\_.py                                                     |        0 |       0 |    100% |
| conftest.py                                                         |        2 |       0 |    100% |
| fixtures/\_\_init\_\_.py                                            |        1 |       0 |    100% |
| fixtures/helper/\_\_init\_\_.py                                     |        1 |       0 |    100% |
| fixtures/helper/deploy\_contract.py                                 |       33 |       2 |     94% |
| fixtures/setup\_ethereum\_test\_environment.py                      |      112 |       6 |     95% |
| rubi\_tests.py                                                      |      326 |       0 |    100% |
| **TOTAL**                                                           | **1303** | **158** | **88%** |
