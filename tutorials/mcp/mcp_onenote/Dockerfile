FROM node:26.13.0-trixie-slim@sha256:5adad64f9a1fca2d51972caa65983634c8a774eb300d72b20f7f2a0f60368072
WORKDIR /app
COPY src/package*.json ./
RUN npm install
COPY src/ .
EXPOSE 3000
CMD ["node", "onenote-sse.mjs"]
