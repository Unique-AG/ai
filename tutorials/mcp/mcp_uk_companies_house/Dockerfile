# Pinned by version and digest, same governed image the platform docker-base uses.
FROM node:26.9.0-trixie-slim@sha256:65f816afd401c1c4de3293acc46dce115398152af4bdcd73c103b096988922d7 AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN sed -i 's/http:\s*true/http: { host: "0.0.0.0" }/' xmcp.config.ts && \
    grep -q '0.0.0.0' xmcp.config.ts || (echo "ERROR: host patch failed" && exit 1)
RUN npm run build

FROM node:26.9.0-trixie-slim@sha256:65f816afd401c1c4de3293acc46dce115398152af4bdcd73c103b096988922d7
WORKDIR /app
COPY --from=build /app/dist ./dist
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/package-lock.json ./package-lock.json
RUN npm ci --omit=dev

USER node
EXPOSE 3001

CMD ["node", "dist/http.js"]
