
<div align="center">
# Machine Learning Operations Project

[![python](https://img.shields.io/badge/-Python_3.8_%7C_3.9_%7C_3.10-blue?logo=python&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![pytorch](https://img.shields.io/badge/PyTorch_2.0+-ee4c2c?logo=pytorch&logoColor=white)](https://pytorch.org/get-started/locally/)
[![lightning](https://img.shields.io/badge/-Lightning_2.0+-792ee5?logo=pytorchlightning&logoColor=white)](https://pytorchlightning.ai/)
[![hydra](https://img.shields.io/badge/Config-Hydra_1.3-89b8cd)](https://hydra.cc/)
[![black](https://img.shields.io/badge/Code%20Style-Black-black.svg?labelColor=gray)](https://black.readthedocs.io/en/stable/)
[![isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/) 
![Huggingface](https://img.shields.io/badge/-HuggingFace-FDEE21?style=for-the-badge&logo=HuggingFace&logoColor=black)  <br>
[![codecov](https://codecov.io/gh/ashleve/lightning-hydra-template/branch/main/graph/badge.svg)](https://codecov.io/gh/ashleve/lightning-hydra-template)  <br>
![AWS](https://img.shields.io/badge/AWS-%23FF9900.svg?style=for-the-badge&logo=amazon-aws&logoColor=white)
![DVC](https://img.shields.io/badge/DVC-945DD6?style=for-the-badge&logo=dvc&logoColor=white)
![Amazon S3](https://img.shields.io/badge/Amazon%20S3-FF9900?style=for-the-badge&logo=amazons3&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white) <br>
![GitHub Actions](https://img.shields.io/badge/github%20actions-%232671E5.svg?style=for-the-badge&logo=githubactions&logoColor=white)
![VS Code Insiders](https://img.shields.io/badge/VS%20Code%20Insiders-35b393.svg?style=for-the-badge&logo=visual-studio-code&logoColor=white)
![Git](https://img.shields.io/badge/git-%23F05033.svg?style=for-the-badge&logo=git&logoColor=white)
![GitHub](https://img.shields.io/badge/github-%23121011.svg?style=for-the-badge&logo=github&logoColor=white)
![Kaggle](https://img.shields.io/badge/Kaggle-035a7d?style=for-the-badge&logo=kaggle&logoColor=white) <br>

![K8S]() <br>

[![license](https://img.shields.io/badge/License-MIT-green.svg?labelColor=gray)](https://github.com/ashleve/lightning-hydra-template#license)


## Main Technologies

[PyTorch Lightning](https://github.com/PyTorchLightning/pytorch-lightning) - a lightweight PyTorch wrapper for high-performance AI research. Think of it as a framework for organizing your PyTorch code.

[Hydra](https://github.com/facebookresearch/hydra) - a framework for elegantly configuring complex applications. The key feature is the ability to dynamically create a hierarchical configuration by composition and override it through config files and the command line.

[DVC](https://dvc.org/) - A tool designed to handle large datasets and machine learning models in a version-controlled workflow

[Tensorboard|wandb](https://www.tensorflow.org/tensorboard) - TensorBoard is a tool that provides visualization and debugging capabilities for TensorFlow and PyTorch experiments. It’s a popular choice for monitoring machine learning training processes in real time.

[AWS|EC2|S3|Lambda|ECR](https://aws.amazon.com/ec2/) - AWS Elastic Compute Cloud (EC2) is a service that provides scalable virtual computing resources in the cloud.

[Docker](https://www.docker.com/) - A platform for creating, deploying, and managing lightweight, portable, and scalable containers.

[FastAPI|Gradio](https://www.gradio.app/) - A Python library for building simple, interactive web interfaces for machine learning models and APIs.

[Nextjs]() - Frontend FrameWork

[K8s|KNative|Kserve|Istio|ArgoCD]() - AWS Kubernets and ArgoCD 

[Prometheus|Grafana] - observability



</div>



# Data Source
### Download Dataset
```bash
chmod +x shscripts/download_zips.sh && ./shscripts/download_zips.sh
```
### Sports
```bash
data/processed/sports/
├── sports.csv
├── test
│   ├── air hockey
│   ├── .
│   ├── .
│   ├── .
│   └── wingsuit flying
├── train
│   ├── air hockey
│   ├── .
│   ├── .
│   ├── .
│   └── wingsuit flying
└── valid
    ├── air hockey
    ├── .
    ├── .
    ├── .
    └── wingsuit flying
-----------------------------------------------------
data/processed/vegfruits/
```


# Install Dependencies
```bash
uv sync --extra cpu   # install torch-cpu version
uv sync --extra cu124 # install torch-gpu version  cu124
uv sync --group develop --group visuals --group testing --group prod --extra cpu
uv sync --group develop --group visuals --group testing --group prod --extra cu124   # install deps from all
uv run --env-file .env --extra cpu
```

# Model Development Phase:
## Hparams Search

```bash
make hsports   # make sure comment that pretrained model and run longer epoch & max to n_trails
```
```yaml
experiment: hsports
hydra:
    sweeper:
        n_trails: 26  # variation of models
    params:
      ++model.stem_type: choice('patch','overlap')
      ++model.act_layer: choice('relu','gelu')
      ++model.global_pool: choice('avg','fast')
      ++model.depths: "[2,2,6,2],[3,3,9,3]"
      ++model.dims: "[24,48,22,168],[12,32,44,96]"
      ++model.kernel_sizes: "[3, 5, 7, 9],[3,3,3,3]"
      ++model.use_pos_emb: "[False,True,False,False], [True,True,True,False]"
trainer:
    max_epochs: 10
```
## Train Model
```yaml
experiment: tsports
script: true
name: sports
callbacks.model_checkpoint.filename: sports
```

```bash
make tsports   # uncomment the pretrained model to save time.
```
## Evaluate Model
- [X] Check Test Metrics
- [X] Save Models
    - [X] checkpoints
    - [X] torchscript
        - [X] cpu
        - [X] gpu
    - [X] onnx
- [X] Explore Dataset
    - [X] Class Distribution
    - [X] Batch Images
- [X] Condusion Matrixs
    - [X] Train
    - [X] Test
    - [X] Validation
 
```bash
make esports   # plot_confusion metrics
```

## Visualize Graphs
```bash
make show
make showoff
```

## Gradio Locally
```bash
make gsports
open http://0.0.0.0:7860/
```


## TorchServe Locally

```bash
export ENABLE_TORCH_PROFILER=true
```
```properties
enable_envvars_config=true
```


```bash
torch-model-archiver  \
    --model-name sports \
    --version 1.0  \
    --export-path ./model_stores/mar_sports \
    --hander  ./src/backend/torchserve_app/sports_handler.py  \
    --serialized-file ./checkpoints/pths/sports.pt \
    --extra-files index_to_name.json \

```



# ON Docker 

```bash
# github.com/moby/moby/issues/12886#issuecomment-480575928
export DOCKER_BUILDKIT=1
```

# Usage for deployment (currently in local)

Basic train

- `uv run python src/backend/torch_local/train.py experiment=hvegfruits script=true`
- `uv run python src/backend/torch_local/train.py experiment=hsports script=true`

scripts takes care of creating onnx model in checkpoints folder

Eval

- `uv run python src/backend/torch_local/eval.py experiment=evegfruits`
- `uv run python src/backend/torch_local/eval.py experiment=esports`

Take the model and host it with fast api

- host one api in 8080 and another api in 9090

- `uv run python src/backend/fastapi_app/fapi_vegfruits.py` 
- `uv run python src/backend/fastapi_app/fapi_sports.py` 

**Next JS**
There are two choosing buttons and each one redirects to different end points
- End points can be changed in `src/frontend/ui/app/predict_app1` and `src/frontend/ui/app/predict_app2`

- npm run dev
