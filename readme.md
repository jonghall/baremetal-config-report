
## Login into Bluemix Containers
```
bx login 
bx cs init
```

## Building Docker Container & Push to Bluemix Registry

```
bx cr login
docker build -t <registry>/bmxbillingreport:latest .
docker push <registry>/bmxbillingreport:latest
bx cr images
```


## Verify Kubernetes Cluster
```
bx cs cluster-config kubetest
kubectl get nodes
kubectl proxy&
```

_Go to http://127.0.0.1:8001/ui_

## Create Service & Define ingress point (modify myingress.yaml to include your host & secretName)
```
kubectl apply -f baremetal-config-report-service.yaml
kubectl apply -f baremetal-config-report-ingress.yaml
kubectl get svc
```


## Deploy Application to Kubernetes Cluster
```
kubectl create -f baremetal-config-report-deployment.yaml
kubectl get nodes
kubectl get deployments
kubectl rollout status deployment/baremetal-config-report-deployment
kubectl get pods --show-labels
```




