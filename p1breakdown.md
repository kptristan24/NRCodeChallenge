# Problem 1 Writeup



#### An "optimized" command to quickly grep logs for the number of days an API was used.

##### Note: You will need to use the GNU fgrep/grep for this to operate.
Most MacOS distros will use the BSD coreutils by default.
The -m option operates globally in BSD (IE, stops searching entirely on first match), for this instance we wanted to optimize searching time by only matching the first instance per file of "api".
Since GNU -m operates as first match per file, you'll need to ensure you're using that.

`brew install grep`

Then make sure you use the correct one when executing the command. You should be able to see where you just installed it.

```LC_ALL=C /usr/local/opt/grep/libexec/gnubin/fgrep -rl -m 1 "/api" log/web/ | wc -l```

##### Breakdown:

`LC_ALL=C`: set to severely cut down on read/opens for pattern matching since we're only matching ASCII characters.

`/usr/local/opt/grep/libexec/gnubin/fgrep`: Specifies GNU fgrep, since I use a Mac.
This will be the default location for most but not all.
Since the problem specified this as a one-off script I wrote it as if it were so, just for me.

`-r -m 1`: -r for recursive search
-m 1: for matching first instance per file _only_.
This greatly optimizes our query as log files can be massive and we only need to know if it happened *at least once* that day.

`"/api"`: endpoint to search for

`log/web/`: root directory to look for matches

`wc -l`: The output of grep is piped to word count for lines, thusly returning the "number of days" the api was used.
