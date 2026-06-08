FROM node:20-alpine AS build

WORKDIR /app

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ .
RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

RUN cat > /etc/nginx/conf.d/default.conf << 'EOF'
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    gzip on;
    gzip_types text/css application/javascript application/json image/svg+xml;
    gzip_min_length 256;

    location /api/ {
        proxy_pass __BACKEND_URL__/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    location /health {
        default_type application/json;
        return 200 '{"status":"ok","service":"frontend"}';
        add_header Content-Type application/json;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF

EXPOSE 80

CMD ["sh", "-c", "sed -i 's|__BACKEND_URL__|'\"${BACKEND_URL}\"'|g' /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
