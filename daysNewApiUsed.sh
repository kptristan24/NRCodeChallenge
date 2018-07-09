#1/bin/bash
LC_ALL=C /usr/local/opt/grep/libexec/gnubin/fgrep -r -m 1 "/api" log/web/ | wc -l
