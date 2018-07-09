# "What Went Wrong" Writeup

##### Cause of the problem:

* *On line 283 we're attempting to use headers_sent as a pythonic property.
Since we're taking advantage of any of the benefits of this type, my recommended remedy is to remove the @property tag and use this as a regular class attribute.
This should be effective as the rest of the code references headers_sent in this manner and I was able to test and see expected behavior again.
(IE, prepending fuzzy to the iterable returned)*
