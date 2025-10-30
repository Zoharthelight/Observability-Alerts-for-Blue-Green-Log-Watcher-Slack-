#!/bin/bash
# verify_failover.sh  - quick local verifier
URL="http://localhost:8080/version"
LOOP=40
SLEEP=0.2

ok=0
bad=0
blue_count=0
green_count=0

for i in $(seq 1 $LOOP); do
  out=$(curl -s -D - $URL -o /dev/null)
  status=$(echo "$out" | head -n 1 | awk '{print $2}')
  pool=$(echo "$out" | grep -i "X-App-Pool:" | awk '{print $2}' | tr -d '\r')
  if [ "$status" = "200" ]; then
    ok=$((ok+1))
    if [ "$pool" = "blue" ]; then blue_count=$((blue_count+1)); fi
    if [ "$pool" = "green" ]; then green_count=$((green_count+1)); fi
  else
    bad=$((bad+1))
  fi
  sleep $SLEEP
done

echo "Requests: $LOOP, OK: $ok, BAD: $bad, BLUE: $blue_count, GREEN: $green_count"
