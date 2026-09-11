FROM node:26.8-trixie-slim@sha256:14bf3eac4bf209d906d3c41256597d3ab1f926b2e93a79e9bdfe1efd32454239
WORKDIR /app
COPY src/package*.json ./
RUN npm install
COPY src/ .
EXPOSE 3000
CMD ["node", "onenote-sse.mjs"]
