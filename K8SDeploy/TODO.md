2024-04-14

1. Fix Kubernetes app storage urls with vegfruits and sports location, check if we need to use two MODEL_URLS
2. Make sure when train.py is triggered, it stores the best model files to S3 location for both models
3. Then another script transfer_mar.py takes that from S3 location and transfers as .mar files

Github actions
1. Once pull request is triggered github actions is triggered, Open an EC2 instance
2. Use train.py, transfer_mar.py and get the final models after training in S3
3. Install eksctl, kubectl, argocd , then do deployment via actions
4. Check scaling/load test and note the results
5. Comment it in pull request

-----------
<debug>

kubectl exec pods/imagenet-classifier-1-predictor-00001-deployment-6f997448fpxqzl   -it --namespace default /bin/bash

kubectl exec --stdin --tty shell-demo -- /bin/bash

kubectl exec mypod -c ruby-container -i -t -- bash -il
</debug>
-----------------