FROM node:20-alpine3.19 AS build

ENV AJV_CLI_VERSION=5.0.0
ENV AJV_FORMATS_VERSION=2.1.0

# install ajv-cli and ajv-formats globally
RUN apk add --no-cache make gcc g++ python3 && \
    npm install -g "ajv-cli@${AJV_CLI_VERSION}" "ajv-formats@${AJV_FORMATS_VERSION}" && \
    npm cache clean --force && \
    apk del make gcc g++ python3

# create small runtime image out of the build image
FROM node:20-alpine3.19
COPY --from=build /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=build /usr/local/bin /usr/local/bin

ENTRYPOINT ["ajv"]
CMD ["help"]
