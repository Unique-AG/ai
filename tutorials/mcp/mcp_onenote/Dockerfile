FROM node:26.5.1-trixie-slim@sha256:deae974a69e140f44f434ab29cb519fb5f8fe250fd364b8ca446bd0761acdc6a
WORKDIR /app
COPY src/package*.json ./
RUN npm install
COPY src/ .
EXPOSE 3000
CMD ["node", "onenote-sse.mjs"]
