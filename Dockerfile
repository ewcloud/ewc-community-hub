FROM docker.io/node:24-alpine 

ENV NODE_ENV=production
WORKDIR /opt/validator

COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts && npm cache clean --force

ENV PATH="/opt/validator/node_modules/.bin:${PATH}"

WORKDIR /
ENTRYPOINT ["ajv"]
CMD ["help"]
