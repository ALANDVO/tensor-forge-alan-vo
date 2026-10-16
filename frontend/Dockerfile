FROM node:24-alpine AS builder
WORKDIR /build
RUN addgroup -S appgroup && adduser -S -G appgroup appuser
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npx vite build

FROM node:24-alpine AS runtime
WORKDIR /app
RUN addgroup -S appgroup && adduser -S -G appgroup appuser
COPY --from=builder /build/dist /app/dist
COPY --from=builder /build/static-server.mjs /app/static-server.mjs
COPY frontend/package.json /app/package.json
ENV NODE_ENV=production \
    PORT=80
EXPOSE 80
USER appuser
HEALTHCHECK --interval=20s --timeout=3s --retries=3 \
  CMD node --input-type=commonjs -e "const http=require('http');const r=http.get('http://127.0.0.1:80/',res=>{process.exit(res.statusCode===200?0:1)});r.on('error',()=>process.exit(1))"
CMD ["node", "static-server.mjs"]