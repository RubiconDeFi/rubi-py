

class Process:
    """this class is really just meant to serve as a place to aggregate useful functionality for processing data. the goal in 
    formatting helper functions in this way is to keep the main processing class for each data source as clean and interoperable as possible.
    """

    def __init__(self):
        self.cowboy = 'hello, defi cowboy. lets get this bread'

    def get_closest_timestamp_value(self, values, timestamp, granularity=60, n=10): 
        """this function takes a dictionary of values (assumes the keys are timestamps) and a timestamp and returns the value of the dictionary that is closest to the timestamp.

        :param values: a dictionary of values with the keys being timestamps
        :type values: dict
        :param timestamp: the timestamp that is of interest
        :type timestamp: int
        :param granularity: the granularity of the timestamps of interest, defaults to 60
        :type granularity: int, optional
        :param n: the optimized search default based upon granularity of which to search , defaults to 10
        :type n: int, optional
        :return: the value of the dictionary that is closest to the timestamp key pair that matches
        :rtype: value
        """

        # based on the granularity of the time perids, get the starting period value 
        timestamp = (timestamp // granularity) * granularity

        # get the keys of the dictionary 
        keys = list(values.keys())

        try: 
            value = values[timestamp]
            return value
        except:
            pass
        
        attempt = 1
        while attempt < n: 
            try: 
                value = values[timestamp + granularity * attempt]
                return value
            except:
                pass

            try:
                value = values[timestamp - granularity * attempt]
                return value
            except:
                pass

            attempt += 1
        
        # if this still doesn't work, search the entire list of keys
        min = abs(keys[0] - timestamp)
        value = values[keys[0]]
        for key in keys[1:]:
            if abs(key - timestamp) < min:
                min = abs(key - timestamp)
                value = values[key]

        return value