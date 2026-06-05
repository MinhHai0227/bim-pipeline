FROM node:22-slim

ENV NODE_ENV=production
ENV PORT=8090
ENV FRAGMENT_WORK_DIR=/tmp/bim-pipeline/ifc

WORKDIR /app

COPY package*.json ./
RUN npm ci --omit=dev

COPY src ./src

EXPOSE 8090

CMD ["npm", "start"]
