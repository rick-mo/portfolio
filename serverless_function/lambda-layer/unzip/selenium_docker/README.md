
docker build -t lambda-selenium .

docker run -v "${PWD}":/var/task lambda-selenium
