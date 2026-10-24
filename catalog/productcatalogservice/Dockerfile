# Upstream productcatalogservice with the extended 200-product catalog.
# Only the data file changes; the service code is Google's.
ARG BASE_IMAGE=us-central1-docker.pkg.dev/online-boutique-ci/microservices-demo/productcatalogservice:v0.10.7
FROM ${BASE_IMAGE}
COPY products.json /src/products.json
