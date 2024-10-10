# This file runs the chap_test docker image specified in compose.test.yml,
# which runs pytest inside the container and checks that the exit code is 0 (i.e. no failed tests)

set -e
docker compose -f compose.yml -f compose.test.yml up --build chap

exit_code=$(docker inspect chap_test --format='{{.State.ExitCode}}')
[ "$exit_code" -eq "0" ] || { echo "Variable is not zero."; exit 1; }
