# decisions and considerations 

### writing to the chain 
throughout the codebase we offer the user the option to pass in a nonce argument or derive it from chain state if none is provided (via the `get_nonce` function). aspirationally, we want 
to support a python based nonce manager that can be used to manage nonces for the user. until then, this optional parameter is meant to enable the user to manage nonces themselves. when a
user does not provide a nonce, we derive it from chain state accordingly. in this case, we also wait for the transaction to be confirmed before continueing. if the transaction fails, 
an exception is raised and the program is exited. the user can override this behavior by managing nonces themselves.