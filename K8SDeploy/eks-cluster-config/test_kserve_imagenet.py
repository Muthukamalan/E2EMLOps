import requests
import json
# cat-classifier
url_1 = "http://a86a7b22b8c09441b8ce16f1f94e6d45-2006895197.ap-south-1.elb.amazonaws.com/v1/models/cat-classifier:predict"

url_2 = "http://a86a7b22b8c09441b8ce16f1f94e6d45-2006895197.ap-south-1.elb.amazonaws.com/v1/models/dog-classifier:predict"

with open("input.json") as f:
    payload = json.load(f)
headers_1 = {"Host": "imagenet-classifier-1.default.emlo.tsai", "Content-Type": "application/json"}

response_1 = requests.request("POST", url_1, headers=headers_1, json=payload)

headers_2 = {"Host": "imagenet-classifier-2.default.emlo.tsai", "Content-Type": "application/json"}

response_2 = requests.request("POST", url_2, headers=headers_2, json=payload)

print(response_1.headers)
print(response_1.status_code)
print(response_1.json())

print("##############")

print(response_2.headers)
print(response_2.status_code)
print(response_2.json())

# http://food-classifier.default.emlo.tsai