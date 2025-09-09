FROM docker.io/node:20-alpine3.19

ENV AJV_CLI_VERSION=5.0.0
ENV AJV_FORMATS_VERSION=2.1.0

RUN apk add --no-cache make gcc g++ python3 && \
    npm install -g "ajv-cli@${AJV_CLI_VERSION}" "ajv-formats@${AJV_FORMATS_VERSION}" && \
    npm cache clean --force && \
    apk del make gcc g++ python3

ENTRYPOINT ["ajv"]
CMD ["help"]
