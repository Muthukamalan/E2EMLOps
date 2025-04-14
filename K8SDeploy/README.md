**docker build**
eval $(minikube -p minikube docker-env)
eval $(minikube docker-env -u) 

**cheatsheet**
kubectl apply -f path_to_yaml.yaml
kubectl get deployment
kubectl get svc
kubectl get pods -o=json
kubectl get ns 

**log suite**
kubectl logs <pod-name> --tail=50 --since=6h --sort-by='.status.containerStatuses[0].restartCount'

**debug suite**
kubectl describe deployment
kubectl describe service/<svc-name>
kubectl describe pod/<pod_name>
kubectl exec -it <pod_name> -- /bin/sh
kubectl port-forward pod/<pod_name> <pod-number>:<local-number> <pod-number>:<local-number>

```note
# Listen on port 8888 on localhost and selected IP, forwarding to 5000 in the pod
kubectl port-forward --address localhost,10.19.21.23 pod/mypod 8888:5000
  
# Listen on a random port locally, forwarding to 5000 in the pod
kubectl port-forward pod/mypod :5000
```


**secret suite**
kubectl create secret
kubectl get secrets
kubectl describe secrets
kubectl delete secret <secret_name>