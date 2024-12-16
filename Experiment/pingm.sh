timestamp=$(date +'%Y_%m_%d_%H_%M_%S')
ping $1 -D -c 100 | awk -F'[ =]' 'BEGIN {print "Name,StepDuration,PlanName,ResultType,Timestamp,TTL,Time(ms)"} /ttl=/{gsub(/\[|\]/, "", $1); split($1, timestamp, ".");  print "ADB Ping Agent,__DURATION_3,PING,ADB Ping Agent," timestamp[1]"," $9 "," $11}' > "$2_ping.csv"

