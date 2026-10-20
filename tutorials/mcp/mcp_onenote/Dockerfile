FROM node:26.12.0-trixie-slim@sha256:0d1e33586362bb9e608c4e751e7a9e7edb55c9ac11461ed5666af696cc461dd4
WORKDIR /app
COPY src/package*.json ./
RUN npm install
COPY src/ .
EXPOSE 3000
CMD ["node", "onenote-sse.mjs"]
