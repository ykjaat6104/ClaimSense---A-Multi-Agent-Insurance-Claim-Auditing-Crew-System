FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["sh", "-c", "sed -i 's|__BACKEND_URL__|'\"${BACKEND_URL}\"'|g' /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
