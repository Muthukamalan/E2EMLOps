`note`: since we do `kubectl apply -f K8SDeploy/config/` and everything in localhost and ports also same it'll get resolve by only one. if you want to test it out `80`->`70`, `81`->`71` and `82`->`72` in any one of the yaml and test it out


```bash

# minikube start
minikube start --driver=docker --cpus=max --memory=max
# tunnel 
minikube tunnel
# build docker image

# config
kubectl apply -f K8SDeploy/config/



# exec inside pod
kubectl exec -it pod/vegfruits-deployment-6f96d7c56f-5st4d -- bash

# 
kubectl get ing

# 
curl -v sports.localhost:80/ping
curl -v vegfruits.localhost:80/ping

curl -v sports.localhost:81/models
curl -v vegfruits.localhost:81/models

curl -v sports.localhost:81/metrics
curl -v vegfruits.localhost:81/metrics


curl -v sports.localhost:80/predictions/msports -F 'data=@data/processed/sports/train/speed skating/001.jpg'
curl -v vegfruits.localhost:80/predictions/mvegfruits -F 'data=@data/processed/vegfruits/validation/lettuce/Image_8.jpg'
```