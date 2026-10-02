# Pinned by version and digest, same governed image the platform docker-base uses.
FROM node:26.10.0-trixie-slim@sha256:ec7758ee051e457b468b32bde57b0879010b325bb9862718e9615225ce4aaae1 AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN sed -i 's/http:\s*true/http: { host: "0.0.0.0" }/' xmcp.config.ts && \
    grep -q '0.0.0.0' xmcp.config.ts || (echo "ERROR: host patch failed" && exit 1)
RUN npm run build

FROM node:26.10.0-trixie-slim@sha256:ec7758ee051e457b468b32bde57b0879010b325bb9862718e9615225ce4aaae1
WORKDIR /app
COPY --from=build /app/dist ./dist
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/package-lock.json ./package-lock.json
RUN npm ci --omit=dev

USER node
EXPOSE 3001

CMD ["node", "dist/http.js"]
