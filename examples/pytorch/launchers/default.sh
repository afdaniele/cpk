#!/usr/bin/env python3

from datetime import datetime
print("===============================================================")
print("Importing PyTorch")
pre = datetime.now()
try:
    import torch
except Exception as e:
    print("PyTorch Import Error!")
    print(e)
    exit(0)
now = datetime.now() - pre
print("PyTorch import success! Total {} seconds".format(now.seconds))

# Check Pytorch Version
print('PyTorch version: ' + torch.__version__)

# Check PyTorch CUDA Version
print('Pytorch CUDA available: ' + str(torch.cuda.is_available()))
if torch.cuda.is_available():
    print('+    CUDA version: ' + str(torch.version.cuda))

# Check Pytorch CUDNN
print('Pytorch cuDNN available: ' + str(torch.backends.cudnn.enabled))
if torch.backends.cudnn.enabled:
    print('+    cuDNN version: ' + str(torch.backends.cudnn.version()))

# Cgheck PyTorch Device Writability
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
if device.type == 'cuda':
    print ("Pytoch has GPU: True")
    print ("+    GPU Name: " + str(torch.cuda.get_device_name(0)))
    print (" Testing to Write to GPU... This will take a while if on Jetson...")
    pre = datetime.now()
    try:
        torch.rand(10, device=device)
        diff = datetime.now() - pre
        print("+    Write to GPU success! Total {} Seconds".format(diff.seconds))
    except Exception:
        print("ERROR! Pytorch sees GPU, but it cannot use it. Are you using a recent generation GPU?")
else:
    print ("Pytoch has GPU: False")
print("===============================================================")
exit()