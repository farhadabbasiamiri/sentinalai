FROM node:24-alpine
<<<<<<< HEAD
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
=======

WORKDIR /app
# Run as the unprivileged "node" user that ships with the official image.
RUN chown node:node /app
USER node

COPY --chown=node:node frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY --chown=node:node frontend ./

>>>>>>> 4f3f30c (feat:Phase 6 -Testing, Security and DevOps)
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
