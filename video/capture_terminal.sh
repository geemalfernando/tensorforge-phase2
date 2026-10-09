#!/bin/zsh
# Captures real terminal sessions for the video. Output: $OUT/<name>.txt with "$ cmd" lines then output.
B=http://localhost:8765; K=demo-video-key; OUT=$1; mkdir -p $OUT
show() { local f=$1; shift; print -r -- "\$ $1" >> $OUT/$f.txt; eval "$2" 2>&1 | cat >> $OUT/$f.txt; print >> $OUT/$f.txt; }
rm -f $OUT/auth.txt $OUT/errors.txt $OUT/jobs.txt
T='{"ticket_id":"TF-1048","channel":"chat","text":"mage order eka late, refund ekak denna"}'
show auth "curl -s \$URL/health" "curl -s -w '   → HTTP %{http_code}' $B/health"
show auth "curl -s \$URL/predict -H 'Content-Type: application/json' -d '{...}'          # no key" "curl -s -w '   → HTTP %{http_code}' -H 'Content-Type: application/json' -d '$T' $B/predict"
show auth "curl -s \$URL/predict -H 'X-API-Key: wrong-key' ...                           # wrong key" "curl -s -w '   → HTTP %{http_code}' -H 'X-API-Key: wrong' -H 'Content-Type: application/json' -d '$T' $B/predict"
show auth "curl -s \$URL/predict -H \"X-API-Key: \$API_KEY\" -H 'Content-Type: application/json' -d '$T'" "curl -s -w '   → HTTP %{http_code}' -H 'X-API-Key: $K' -H 'Content-Type: application/json' -d '$T' $B/predict | python3 -c 'import sys;d=sys.stdin.read();print(d.replace(\",\\\"\",\",\\n  \\\"\"))'"
show auth "curl -s \$URL/predict -H \"Authorization: Bearer \$API_KEY\" ... -o /dev/null" "curl -s -o /dev/null -w '→ HTTP %{http_code}' -H 'Authorization: Bearer $K' -H 'Content-Type: application/json' -d '$T' $B/predict"
show errors "curl -s \$URL/predict -H \"X-API-Key: \$API_KEY\" -H 'Content-Type: application/json' -d '{\"channel\": \"chat\",'" "curl -s -w '   → HTTP %{http_code}' -H 'X-API-Key: $K' -H 'Content-Type: application/json' -d '{\"channel\": \"chat\",' $B/predict"
show errors "curl -s \$URL/predict ... -d '{\"channel\":\"sms\",\"text\":\"   \"}'" "curl -s -w '   → HTTP %{http_code}' -H 'X-API-Key: $K' -H 'Content-Type: application/json' -d '{\"channel\":\"sms\",\"text\":\"   \"}' $B/predict"
show errors "curl -s \$URL/predict ... -H 'Content-Type: text/plain' -d 'hello'" "curl -s -w '   → HTTP %{http_code}' -H 'X-API-Key: $K' -H 'Content-Type: text/plain' -d 'hello' $B/predict"
show errors "curl -s \$URL/predict/batch ... -d '{\"tickets\":[{\"ticket_id\":\"A\",...},{\"ticket_id\":\"A\",...}]}'" "curl -s -w '   → HTTP %{http_code}' -H 'X-API-Key: $K' -H 'Content-Type: application/json' -d '{\"tickets\":[{\"ticket_id\":\"A\",\"channel\":\"chat\",\"text\":\"hi\"},{\"ticket_id\":\"A\",\"channel\":\"chat\",\"text\":\"hi\"}]}' $B/predict/batch"
show errors "curl -s \$URL/no-such-route" "curl -s -w '   → HTTP %{http_code}' $B/no-such-route"
python3 -c "import json;print(json.dumps({'tickets':[{'ticket_id':'EVAL-%04d'%i,'channel':['chat','email','call_transcript'][i%3],'text':['my order is two hours late','charged twice for one ride','left my phone in the car','app crashes at checkout'][i%4]+' #%d'%i} for i in range(3000)]}))" > /tmp/tf_job_3000.json 2>/dev/null || true
cp /tmp/tf_job_3000.json $OUT/job.json 2>/dev/null
show jobs "curl -s -i \$URL/batch/jobs -H \"X-API-Key: \$API_KEY\" -H 'Idempotency-Key: eval-run-1' -H 'Content-Type: application/json' --data-binary @job_3000.json" "curl -s -i -H 'X-API-Key: $K' -H 'Idempotency-Key: eval-run-1' -H 'Content-Type: application/json' --data-binary @$OUT/job.json $B/batch/jobs | grep -iE '^(HTTP|location|retry-after)|job_id' | tr -d '\r'"
ID=$(curl -s -H "X-API-Key: $K" -H 'Idempotency-Key: eval-run-1' -H 'Content-Type: application/json' --data-binary @$OUT/job.json $B/batch/jobs | python3 -c 'import sys,json;print(json.load(sys.stdin)["job_id"])')
show jobs "curl -s \$URL/batch/jobs/\$JOB/results -H \"X-API-Key: \$API_KEY\"        # too early" "curl -s -w '   → HTTP %{http_code}' -H 'X-API-Key: $K' $B/batch/jobs/$ID/results"
sleep 4
show jobs "curl -s \$URL/batch/jobs/\$JOB -H \"X-API-Key: \$API_KEY\"" "curl -s -w '   → HTTP %{http_code}' -H 'X-API-Key: $K' $B/batch/jobs/$ID | python3 -c 'import sys;d=sys.stdin.read();print(d.replace(\",\\\"\",\",\\n  \\\"\"))' | grep -E 'status|total|processed|HTTP'"
show jobs "curl -s '\$URL/batch/jobs/\$JOB/results?offset=0&limit=2' -H \"X-API-Key: \$API_KEY\"" "curl -s -w '   → HTTP %{http_code}' -H 'X-API-Key: $K' '$B/batch/jobs/$ID/results?offset=0&limit=2' | python3 -c 'import sys;d=sys.stdin.read();print(d.replace(\"{\\\"category\",\"\\n  {\\\"category\").replace(\"],\\\"\",\"],\\n\\\"\"))'"
show jobs "curl -s \$URL/batch/jobs/unknown-id -H \"X-API-Key: \$API_KEY\"" "curl -s -w '   → HTTP %{http_code}' -H 'X-API-Key: $K' $B/batch/jobs/unknown-id"
