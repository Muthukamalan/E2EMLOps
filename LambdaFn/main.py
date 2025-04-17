import json
import os
import platform
import socket
from datetime import datetime
from timeit import default_timer as timer

import gradio as gr
import psutil
import torch
from PIL import Image
from torchvision import transforms

notes = f"System Details:: {platform.system()}-{platform.release()}\nArchitecture: {platform.architecture()[0]}\nSocketName: {socket.getfqdn()}\nHostname:: {socket.gethostname()}\nCPU count:: {psutil.cpu_count(logical=True)}\nBoot time: { datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S") }\nUPtime:: {str(datetime.now()-datetime.fromtimestamp( psutil.boot_time() )).split('.')[0]}(HH:MM:SS)"

torch.set_float32_matmul_precision("medium")
device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
torch.autocast(enabled=True, dtype="float16", device_type="cuda")
torch.set_default_device(device=torch.device("cpu"))

###########################################################################################################
## # Read From S3
## BUCKET_NAME = 'emlo-project'
## ARTIFACTS   = ['checkpoints/pths/sports_cpu.pt','checkpoints/pths/vegfruits_cpu.pt','checkpoints/classnames/sports.json','checkpoints/classnames/vegfruits.json']
## # makedirs
## os.makedirs(exist_ok=True,name='checkpoints')
## os.makedirs(exist_ok=True,name=os.path.join('checkpoints','pths'))
## os.makedirs(exist_ok=True,name=os.path.join('checkpoints','classnames'))
## # s3 client
## s3_client   = boto3.client("s3",aws_access_key_id= os.getenv('AWS_ACCESS_KEY_ID'), aws_secret_access_key= os.getenv('AWS_SECRET_ACCESS_KEY'), region_name='ap-south-1')
## for artifact in ARTIFACTS: s3_client.download_file(BUCKET_NAME,artifact,artifact)
## print(f"accesskey_id: {os.getenv('AWS_ACCESS_KEY_ID')}")
###########################################################################################################


# Define a no-op flagging callback
class NoOpFlaggingCallback(gr.FlaggingCallback):
    def setup(self, components, flagging_dir):
        pass  # Override setup to prevent directory creation

    def flag(self, flag_data, flag_option=None, flag_index=None, username=None):
        pass  # Do nothing when a flag is submitted


TEST_TRANSFORMS = transforms.Compose(
    [
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)


def load_model(name: str, path_dir: str = ".") -> torch.nn.Module:
    if torch.cuda.is_available():
        model = torch.jit.load(os.path.join(path_dir, f"{name}.pt"))
    else:
        model = torch.jit.load(os.path.join(path_dir, f"{name}_cpu.pt"))
    return model


smodel = load_model(
    path_dir=os.path.join(os.getcwd(), "checkpoints", "pths"), name="sports"
)
vfmodel = load_model(
    path_dir=os.path.join(os.getcwd(), "checkpoints", "pths"), name="vegfruits"
)


# ' r'./checkpoints/classnames/sports.json'
with open(
    os.path.join(os.getcwd(), "checkpoints", "classnames", "sports.json")
) as class2idxfile:
    scls2lbs: dict = json.load(class2idxfile)
# r'./checkpoints/classnames/vegfruits.json'
with open(
    os.path.join(os.getcwd(), "checkpoints", "classnames", "vegfruits.json")
) as class2idxfile:
    vfcls2lbs: dict = json.load(class2idxfile)


sidx2lbl = {v: k for k, v in scls2lbs.items()}
sclass_idx = list(sidx2lbl.values())


vfidx2lbl = {v: k for k, v in vfcls2lbs.items()}
vfclass_idx = list(vfidx2lbl.values())


@torch.no_grad()
def spredict_fn(img: Image):
    start_time = timer()
    try:
        img = TEST_TRANSFORMS(img=img).to(device)
        logits = smodel(img.unsqueeze(0))
        probabilites = torch.softmax(logits, dim=-1)
        res = {}

        i2ls, pos = torch.topk(probabilites, k=5, dim=-1)

        for label, conf in zip(
            [sidx2lbl[i.item()] for i in pos[0]],
            [i.item() for i in i2ls[0]],
            strict=False,
        ):
            res[label] = conf

        pred_time = round(timer() - start_time, 5)
        return (res, pred_time)
    except Exception as e:
        print(f"error:{str(e)}")
        gr.Error("An error occured 💥!", duration=5)
        return ({"Title ☠️": 0.0}, 0.0)


@torch.no_grad()
def vfpredict_fn(img: Image):
    start_time = timer()
    try:
        img = TEST_TRANSFORMS(img=img).to(device)
        logits = vfmodel(img.unsqueeze(0))
        probabilites = torch.softmax(logits, dim=-1)
        res = {}

        i2ls, pos = torch.topk(probabilites, k=5, dim=-1)

        for label, conf in zip(
            [vfidx2lbl[i.item()] for i in pos[0]],
            [i.item() for i in i2ls[0]],
            strict=False,
        ):
            res[label] = conf

        pred_time = round(timer() - start_time, 5)
        return (res, pred_time)
    except Exception as e:
        print(f"error:{str(e)}")
        gr.Error("An error occured 💥!", duration=5)
        return ({"Title ☠️": 0.0}, 0.0)


sports_interface = gr.Interface(
    fn=spredict_fn,
    inputs=gr.Image(type="pil"),
    outputs=[
        gr.Label(num_top_classes=5, label="predictions"),
        gr.Number(label="Prediction Time(s)"),
    ],
    title="Let's DO it!!",
    description="If data were a sport, I'll be the champion by now!!",
    article=f"<h3>Created by muthukamalan.m ❤️</h3><pre>{notes}</pre>",
    cache_examples=True,
    flagging_options=[],
    flagging_callback=NoOpFlaggingCallback(),
)

vegfruits_interface = gr.Interface(
    fn=vfpredict_fn,
    inputs=gr.Image(type="pil"),
    outputs=[
        gr.Label(num_top_classes=5, label="predictions"),
        gr.Number(label="Prediction Time(s)"),
    ],
    title="Let's EAT!!",
    description="I'm non-vegetarian only on weekends!!",
    article=f"<h3>Created by muthukamalan.m ❤️</h3><pre>{notes}</pre>",
    cache_examples=False,
    flagging_options=[],
    flagging_callback=NoOpFlaggingCallback(),
)


demo = gr.TabbedInterface(
    tab_names=["Sports", "VegFruits"],
    interface_list=[sports_interface, vegfruits_interface],
    analytics_enabled=True,
)

demo.launch(
    share=False,
    debug=False,
    server_name="0.0.0.0",
    server_port=8080,
    enable_monitoring=False,
)
