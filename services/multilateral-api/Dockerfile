FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod ./
RUN go mod download
COPY . .
RUN go build -o srave-multilateral ./cmd/main.go

FROM alpine:3.19
WORKDIR /app
COPY --from=builder /app/srave-multilateral .
EXPOSE 8003
CMD ["./srave-multilateral"]
