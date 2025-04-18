include .env

help:  ## Show help
	@grep -E '^[.a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'


clean: ## Clean autogenerated files
	rm -rf dist
	find . -type f -name "*.DS_Store" -ls -delete
	find . | grep -E "(__pycache__|\.pyc|\.pyo|.ruff_cache|.venv|\.egg-info|.pytest_cache|.ipynb_checkpoints|.ruff_cache|.gradio)" | xargs rm -rf
	rm -f .coverage
	find . -type f -name "uv.lock" -ls -delete
	

clean-logs: ## Clean logs
	find . -type f -name "*.log" -ls -delete
	find multirun/** -type d -exec rm -rf {} + 2>/dev/null
	find logs/** -type d -exec rm -rf {} + 2>/dev/null
	find outputs/** -type d -exec rm -rf {} + 2>/dev/null
	find lightning_logs/** type d -exec rm -rf {} + 2>/dev/null


format: ## Run ruff hooks
	ruff check . --fix

sync: ## syncing data and checkpoints
	dvc pull
	aws s3 cp checkpoints/ s3://emlo-project/checkpoints/ --recursive


del-model:  ## Delete saved model
	find . -type f -name "*.onnx" -ls -delete
	find . -type f -name "*.pt" -ls -delete
	find . -type f -name "*.pth" -ls -delete
	find . -type f -name "*.ckpt" -ls -delete
	find . -type f -name "*.mar" -ls -delete
	


#############################################################################################
# 
#		Tensorboard Dashboard
# 
#############################################################################################

struct: ## show tree structure
	tree -L 4 . --dirsfirst 

show: ## tensorboard logs on fastrun
	tensorboard --logdir logs/ --load_fast=false --bind_all --port 6006 &


showoff: ## turnoff tensorboard
	# kill -9 $(lsof -ti :6006)
	@PID=$$(lsof -ti :6006); \
	if [ -n "$$PID" ]; then \
		echo "Killing process $$PID"; \
		/usr/bin/kill -9 $$PID; \
	else \
		echo "No process found on port 6006"; \
	fi



#############################################################################################
# 
# 		SPORTS MODEL
# 
#############################################################################################
hsports:  ## hparam search on sports ds
	HYDRA_FULL_ERROR=1 python src/backend/torch_local/train.py experiment=hsports  -m
	echo "Best Hparams"
	cat multirun/*/*/optimization_results.yaml

tsports:  ## train model on sports ds
	HYDRA_FULL_ERROR=1 python src/backend/torch_local/train.py script=true name=sports callbacks.model_checkpoint.filename=sports

esports:  ## evaluate model on sports ds
	HYDRA_FULL_ERROR=1 python src/backend/torch_local/eval.py experiment=esports

fsports:  ## fastapi deploy on sports ds
	python src/backend/fastapi_app/fapi_sports.py 

tssports:  ## torchsere deploy sports
	torchserve --start --model-store checkpoints/model_stores/sports/ --ts-config checkpoints/model_stores/sports/config.properties --enable-model-api --disable-token-auth


#############################################################################################
# 
# 		VEG & FRUITS MODEL
# 
#############################################################################################
hvegfruits:  ## hparam search on vegfruits ds
	echo "TODO: hparam search vegfruits"

tvegfruits:  ## train search on vegfruits ds
	python src/backend/torch_local/train.py model=mvegfruits data=dvegfruits script=true name=vegfruits callbacks.model_checkpoint.filename=vegfruits

evegfruits:  ## evaluate model on vegfruits ds
	HYDRA_FULL_ERROR=1 python src/backend/torch_local/eval.py experiment=evegfruits

fvegfruits:  ## fastapi deploy on vegfruits ds
	python src/backend/fastapi_app/fapi_vegfruits.py 

tsvegfruits:  ## torchsere deploy vegfruits
	torchserve --start --model-store checkpoints/model_stores/vegfruits/ --ts-config checkpoints/model_stores/vegfruits/config.properties --enable-model-api --disable-token-auth

#############################################################################################
# 
# 		GRADIO Deploy
# 
#############################################################################################
gradio-deploy-locally:  ## deploy gradio on locally
	python LambdaFn/main.py 



#############################################################################################
# 
# 		TORCHSERVE Deploy
# 
#############################################################################################
tserve-make-mars:  ## make mar files for torchserve
	torch-model-archiver --model-name msports --serialized-file checkpoints/onnxs/sports.onnx --handler src/backend/torchserve_app/sports_handler.py --export-path checkpoints/model_stores/sports/ -f --version 0.0.1 --extra-files checkpoints/model_stores/sports/index_to_name.json -r checkpoints/model_stores/sports/requirements.txt 
	torch-model-archiver --model-name mvegfruits --serialized-file checkpoints/onnxs/vegfruits.onnx --handler src/backend/torchserve_app/vegfruits_handler.py --export-path checkpoints/model_stores/vegfruits/ -f --version 0.0.1 --extra-files checkpoints/model_stores/vegfruits/index_to_name.json -r checkpoints/model_stores/sports/requirements.txt 
tserve-stop:       ## torchserve stop
	torchserve --stop
tserve-docker-build: ## build docker image for torchserve deployment
	docker build -t dtssports:latest -f Dockerfile.ts.sports .
	docker build -t dtsvegfruits:latest -f Dockerfile.ts.vegfruits .



#############################################################################################
# 
# 		AWS Lambda Fn
# 
#############################################################################################
BUILD_ARGS := $(shell grep -v '^#' .env | xargs -I {} echo --build-arg {})
lambda-docker-build:
	# makesure you do `docker logout public.ecr.aws`  ## thread, 🧵 https://stackoverflow.com/questions/76975954/docker-pull-from-public-ecr-aws-results-in-403-forbidden-error

	# TO login, `aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin ${CDK_DEFAULT_ACCOUNT}.dkr.ecr.ap-south-1.amazonaws.com`
	docker build ${BUILD_ARGS} -t awslambdafn  -f Dockerfile.lambdafn .
	docker run --rm -it -d -p 8080:8080 --name lambdacontainer awslambdafn