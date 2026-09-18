FROM node:26.9.0-trixie-slim@sha256:65f816afd401c1c4de3293acc46dce115398152af4bdcd73c103b096988922d7
WORKDIR /app
COPY src/package*.json ./
RUN npm install
COPY src/ .
EXPOSE 3000
CMD ["node", "onenote-sse.mjs"]
