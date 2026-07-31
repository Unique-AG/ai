# Pinned by version and digest, same governed image the platform docker-base uses.
FROM node:24.18.0-trixie-slim@sha256:ae91dcc111a68c9d2d81ff2a17bda61be126426176fde6fe7d08ab13b7f50573
WORKDIR /app
COPY src/package*.json ./
RUN npm install
COPY src/ .
USER node
EXPOSE 3000
CMD ["node", "onenote-sse.mjs"]
