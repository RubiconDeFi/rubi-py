# rubi-py testing suite

This testing suite covers the rubi-py sdk's entire codebase. Our testing coverage is currently at 50%

## Installation and Setup:

Note: To run tests via poetry, you will need to be on Python 3.10.X. You can check this by running `python --version` or `python3 --version`.

To run the entire test suite, execute the following command in your terminal:

```shell 
    poetry run test
```

To run specific tests, you can use the -k flag followed by the name of the test. For example, to run tests related to adding pairs, you can use:

```shell
    poetry run test -k test_add_pair
```

## Test coverage

To run and generate test coverage, and then view the report on coverage run:

```shell
    poetry run test_with_coverage
```

To generate an html view of coverage run:

```shell
    poetry run generate_coverage_report
```

### Coverage report


| Name                                                                    | Stmts     | Miss  | Cover |
|-------------------------------------------------------------------------|-----------|-------|-------|
| rubi-py/rubi/rubi/__init__.py                                           | 5         | 0     | 100%  |
| rubi-py/rubi/rubi/client.py                                             | 262       | 102   | 61%   |
| rubi-py/rubi/rubi/contracts/__init__.py                                 | 6         | 0     | 100%  |
| rubi-py/rubi/rubi/contracts/base_contract.py                            | 86        | 20    | 77%   |
| rubi-py/rubi/rubi/contracts/contract_types/__init__.py                  | 2         | 0     | 100%  |
| rubi-py/rubi/rubi/contracts/contract_types/events.py                    | 188       | 25    | 87%   |
| rubi-py/rubi/rubi/contracts/contract_types/transaction_receipt.py       | 43        | 4     | 91%   |
| rubi-py/rubi/rubi/contracts/erc20.py                                    | 50        | 7     | 86%   |
| rubi-py/rubi/rubi/contracts/market.py                                   | 52        | 11    | 79%   |
| rubi-py/rubi/rubi/contracts/router.py                                   | 31        | 11    | 65%   |
| rubi-py/rubi/rubi/contracts/transaction_handler.py                      | 47        | 5     | 89%   |
| rubi-py/rubi/rubi/data/__init__.py                                      | 1         | 0     | 100%  |
| rubi-py/rubi/rubi/data/helpers/__init__.py                              | 2         | 0     | 100%  |
| rubi-py/rubi/rubi/data/helpers/query_types.py                           | 9         | 2     | 78%   |
| rubi-py/rubi/rubi/data/helpers/validation.py                            | 26        | 18    | 31%   |
| rubi-py/rubi/rubi/data/market.py                                        | 114       | 60    | 47%   |
| rubi-py/rubi/rubi/network/__init__.py                                   | 1         | 0     | 100%  |
| rubi-py/rubi/rubi/network/network.py                                    | 74        | 20    | 73%   |
| rubi-py/rubi/rubi/rubicon_types/__init__.py                             | 3         | 0     | 100%  |
| rubi-py/rubi/rubi/rubicon_types/erc20_transactions.py                   | 33        | 5     | 85%   |
| rubi-py/rubi/rubi/rubicon_types/orderbook.py                            | 64        | 19    | 70%   |
| rubi-py/rubi/rubi/rubicon_types/orders.py                               | 138       | 26    | 81%   |
| __init__.py                                                             | 0         | 0     | 100%  |
| conftest.py                                                             | 2         | 0     | 100%  |
| fixtures/__init__.py                                                    | 1         | 0     | 100%  |
| fixtures/helper/__init__.py                                             | 2         | 0     | 100%  |
| fixtures/helper/deploy_contract.py                                      | 33        | 2     | 94%   |
| fixtures/helper/execute_transaction.py                                  | 7         | 0     | 100%  |
| fixtures/setup_ethereum_test_environment.py                             | 104       | 7     | 93%   |
| rubi_tests.py                                                           | 495       | 0     | 100%  |
| TOTAL                                                                   | 1881      | 344   | 82%   |
