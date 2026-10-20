# Pinned by version and digest, same governed image the platform docker-base uses.
FROM node:26.12.0-trixie-slim@sha256:0d1e33586362bb9e608c4e751e7a9e7edb55c9ac11461ed5666af696cc461dd4 AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN sed -i 's/http:\s*true/http: { host: "0.0.0.0" }/' xmcp.config.ts && \
    grep -q '0.0.0.0' xmcp.config.ts || (echo "ERROR: host patch failed" && exit 1)
RUN npm run build

FROM node:26.12.0-trixie-slim@sha256:0d1e33586362bb9e608c4e751e7a9e7edb55c9ac11461ed5666af696cc461dd4
WORKDIR /app
COPY --from=build /app/dist ./dist
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/package-lock.json ./package-lock.json
RUN npm ci --omit=dev

USER node
EXPOSE 3001

CMD ["node", "dist/http.js"]
