# mTLS Setup — Internal Service Certificates

## Prerequisites
```bash
brew install cfssl   # macOS
# or
go install github.com/cloudflare/cfssl/cmd/cfssl@latest
go install github.com/cloudflare/cfssl/cmd/cfssljson@latest
```

## 1. Generate Internal CA
```bash
cd infrastructure/mtls
cfssl gencert -initca ca-csr.json | cfssljson -bare ca
# Produces: ca.pem, ca-key.pem, ca.csr
```

## 2. Generate Service Certificates
```bash
# srave-api
cfssl gencert -ca=ca.pem -ca-key=ca-key.pem -config=ca-config.json \
  -profile=server srave-api-csr.json | cfssljson -bare srave-api

# Repeat for each service — copy srave-api-csr.json, change CN and hosts
for svc in spatial-worker billing-worker multilateral-api voice-service; do
  sed "s/srave-api/$svc/g" srave-api-csr.json > ${svc}-csr.json
  cfssl gencert -ca=ca.pem -ca-key=ca-key.pem -config=ca-config.json \
    -profile=server ${svc}-csr.json | cfssljson -bare $svc
done
```

## 3. Store Certs as K3s Secrets
```bash
kubectl create secret generic srave-mtls-certs \
  --from-file=ca.pem \
  --from-file=srave-api.pem \
  --from-file=srave-api-key.pem \
  -n srave
```

## 4. Mount in Services
Add to each K3s deployment spec under `volumeMounts`:
```yaml
volumeMounts:
  - name: mtls-certs
    mountPath: /certs
    readOnly: true
volumes:
  - name: mtls-certs
    secret:
      secretName: srave-mtls-certs
```

## 5. Configure httpx Client (Python services)
```python
import httpx
client = httpx.AsyncClient(
    cert=("/certs/srave-api.pem", "/certs/srave-api-key.pem"),
    verify="/certs/ca.pem",
)
```

## 6. Verify mTLS Active
```bash
# Should fail without client cert
curl https://srave-api.srave.svc.cluster.local/health
# Should succeed with cert
curl --cert srave-api.pem --key srave-api-key.pem --cacert ca.pem \
  https://srave-api.srave.svc.cluster.local/health
```
