just wanted to put some thoughts here on future directions and goals for the data helper functions. in general, our goals should be 
to provide the highest level of access to an end user, while also enabling access to data that necessitates different levels of 
connection. in our current state, we are pretty biased towards optimism and have created functions that are specific to that chains 
structure. this was a good start, but already with the goerli bedrock upgrade we are seeing the drawbacks of this approach. 

going forward, i believe we should strive to create functions that are more dynamic and intuitive. for example, we can have 
functions that read the chain id to then determine which gas calculation to use. moreover, we should strive for an architecture 
that allows for the seamless access of data across multiple chains. this will necessitate some higher level architecture changes,
but i believe it will be worth it in the long run.

if you have any thoughts on this, please feel free to comment here or reach out to me directly. thank you for your time, we are in 
this together. Atra esterní ono thelduin. Mor'ranr lifa unin hjarta onr. Un atra du evarínya ono varda.