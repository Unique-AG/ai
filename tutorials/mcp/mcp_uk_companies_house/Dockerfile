# Pinned by version and digest, same governed image the platform docker-base uses.
FROM node:26.13.1-trixie-slim@sha256:e6bedef217677b276c591795e169840edd9096dbf13f29df8ef8d1856b8820bc AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN sed -i 's/http:\s*true/http: { host: "0.0.0.0" }/' xmcp.config.ts && \
    grep -q '0.0.0.0' xmcp.config.ts || (echo "ERROR: host patch failed" && exit 1)
RUN npm run build

FROM node:26.13.1-trixie-slim@sha256:e6bedef217677b276c591795e169840edd9096dbf13f29df8ef8d1856b8820bc
WORKDIR /app
COPY --from=build /app/dist ./dist
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/package-lock.json ./package-lock.json
RUN npm ci --omit=dev

USER node
EXPOSE 3001

CMD ["node", "dist/http.js"]
