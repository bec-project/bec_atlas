#!/bin/bash

# check if redis is running on port 6380 and mongodb on port 27017 and scylladb on port 9070
if [ "$(nc -z localhost 6380; echo $?)" -ne 0 ]; then
    echo "Redis is not running on port 6380"
    exit 1
fi

if [ "$(nc -z localhost 27017; echo $?)" -ne 0 ]; then
    echo "MongoDB is not running on port 27017"
    exit 1
fi

coverage run --concurrency=thread --source=./backend --omit=*/backend/tests/* -m pytest -v --junitxml=./test_files/report.xml --skip-docker --random-order --full-trace ./backend/tests

EXIT_STATUS=$?

if [ $EXIT_STATUS -ne 0 ]; then
    exit $EXIT_STATUS
fi

coverage report
coverage xml -o ./test_files/coverage.xml
