# Our frontend: Google's frontend source (online-boutique/src/frontend) with our
# change for recommendation API version 2 (a reason under each "You May Also
# Like" product), plus pictures for the products added by generate_catalog.py.
#
# Build from the repository root:
#   docker build -f catalog/frontend/Dockerfile .

ARG BUILDPLATFORM=linux/amd64

FROM --platform=$BUILDPLATFORM golang:1.27.0-alpine@sha256:4c9fe60190a2a3350ddc51de80d0224b8a6698d12bdfc999fee45ea9d6c46dbc AS builder
ARG TARGETOS=linux
ARG TARGETARCH=amd64
WORKDIR /src
COPY online-boutique/src/frontend/go.mod online-boutique/src/frontend/go.sum ./
RUN go mod download
COPY online-boutique/src/frontend/ .
RUN GOOS=${TARGETOS} GOARCH=${TARGETARCH} CGO_ENABLED=0 go build -ldflags="-s -w" -o /go/bin/frontend .

FROM gcr.io/distroless/static
WORKDIR /src
COPY --from=builder /go/bin/frontend /src/server
COPY online-boutique/src/frontend/templates ./templates
COPY online-boutique/src/frontend/static ./static
COPY catalog/frontend/static/img/products/generated ./static/img/products/generated
ENV GOTRACEBACK=single
EXPOSE 8080
ENTRYPOINT ["/src/server"]
