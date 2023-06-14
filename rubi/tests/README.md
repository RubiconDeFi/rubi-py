# rubi-py testing suite

This testing suite covers the rubi-py sdk's entire codebase. Our testing coverage is currently at 50%

## Installation and Setup:

To run the entire test suite, execute the following command in your terminal:
```shell 
    pytest rubi_tests.py
```

To run specific tests, you can use the -k flag followed by the name of the test. For example, to run tests related to adding pairs, you can use:
```shell
    pytest rubi_tests.py -k add_pair
```

To view more detailed output during the test run, you can use the -v flag for a verbose mode:
```shell
    pytest rubi_tests.py -v
```


## Code coverage and tests


| Class         | Function                            | Tests                                                                                                   |
|---------------|-------------------------------------|---------------------------------------------------------------------------------------------------------|
| TestNetwork   | test_init_from_yaml                 | - Checks if network attributes are set correctly                                                        |
| TestClient    | test_init                           | - Checks if client attributes are set correctly                                                         |
|               |                                     | - Checks if market and router attributes are initialized correctly                                      |
|               |                                     | - Checks if _pairs attribute is initialized as an empty dictionary                                      |
|               |                                     | - Checks if message_queue attribute is set to None when no queue is provided                          |
| TestClient    | test_add_pair                       | - Checks if pair is added to the client's pairs list                                                     |
|               |                                     | - Checks if the added pair has the correct base and quote assets                                        |
| TestClient    | test_update_pair_allowance          | - Checks if base and quote asset allowances are updated correctly                                       |
| TestClient    | test_delete_pair                    | - Checks if pair is removed from the client's pairs list                                                 |
| TestClient    | test_get_orderbook                  | - Checks if the orderbook is retrieved correctly for the given pair name                                |
| TestClient    | test_place_buy_market_order         | - Checks if a buy market order is placed successfully                                                   |
|               |                                     | - Checks if the account's balances are updated correctly after placing the order                       |
|               |                                     | - Checks if the offer is no longer in the orderbook after placing the order                            |
| TestClient    | test_place_buy_limit_order          | - Checks if a buy limit order is placed successfully                                                    |
|               |                                     | - Checks if the account's balances are updated correctly after placing the order                       |
|               |                                     | - Checks if the offer is no longer in the orderbook after placing the order                            |
| TestClient    | test_place_sell_market_order        | - Checks if a sell market order is placed successfully                                                  |
|               |                                     | - Checks if the account's balances are updated correctly after placing the order                       |
|               |                                     | - Checks if the offer is no longer in the orderbook after placing the order                            |
| TestClient    | test_place_sell_limit_order         | - Checks if a sell limit order is placed successfully                                                   |
|               |                                     | - Checks if the account's balances are updated correctly after placing the order                       |
|               |                                     | - Checks if the offer is no longer in the orderbook after placing the order                            |
