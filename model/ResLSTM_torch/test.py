# import __init__ as booger
import os.path
import sys

sys.path.insert(1, '/work/hwei/HaowenWeiDeepLearning/MOS_Project/AutoDrive_Project')

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from tqdm import tqdm

from model.CustomDataLoader.dataloader import Custom_DataLoader
from config.training_config import root_data_dir


from model.ResLSTM_torch.Lovasz_Softmax import Lovasz_softmax
from model.ResLSTM_torch.ResLSTM_torch import ResLSTM

nclasses = 3

print(torch.cuda.is_available())
print(torch.cuda.current_device())
print(torch.cuda.get_device_name(0))
device = torch.device('cuda:0')


ResLSTM_model = ResLSTM(nclasses).to(device)
print(torch.cuda.memory_summary())
weight = [0, 9.0, 251.0]
weight=torch.tensor(weight).to(device)

WCE = nn.CrossEntropyLoss(weight=weight, ignore_index=0, reduction='none').to(device)
# NLL = nn.NLLLoss(weight=weight).to(device)
LS = Lovasz_softmax().to(device)

optimizer = torch.optim.AdamW(ResLSTM_model.parameters(), lr=0.001,weight_decay=0.0005)
# scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=1, gamma=0.1)

scaler = torch.cuda.amp.GradScaler()


#################
# data loader
train_data_dir = os.path.join(root_data_dir, 'train_test_val', 'val', 'x')
train_label_dir = os.path.join(root_data_dir, 'train_test_val', 'val', 'y')

train_dataset = Custom_DataLoader(data_dir=train_data_dir, label_dir=train_label_dir)
val_dataset = Custom_DataLoader(data_dir=train_data_dir, label_dir=train_label_dir)

train_loader = DataLoader(dataset=train_dataset, batch_size=2, shuffle=True)
val_loader = DataLoader(dataset=val_dataset, batch_size=2, shuffle=True)
#################


N, T, C = 3, 5, 9

input_tensor = torch.randn(N, T, C, 16, 16).to(device)
semantic_label = np.zeros((N, 1, 16, 16))
semantic_label = torch.from_numpy(semantic_label).to(dtype=torch.long)
semantic_label_mask = torch.ones(N, 1, 16, 16).to(dtype=torch.long)

for current_epoch in tqdm(range(0, 100)):

    print('Epoch: ', current_epoch)

    for batch_index in range(0,10):
        print(optimizer.param_groups[0]['lr'])
        # print('batch_index:', batch_index)


        semantic_label = torch.squeeze(semantic_label, dim=1).to(device)
        semantic_label_mask = torch.squeeze(semantic_label_mask, dim=1)
        with torch.cuda.amp.autocast(enabled=True):
            semantic_output = ResLSTM_model(input_tensor) # (b, c, h, w)
            pixel_losses = WCE(semantic_output, semantic_label)
            print(pixel_losses)
            pixel_losses = pixel_losses.to(device)
            pixel_losses = pixel_losses.contiguous().view(-1)
            loss_ce = pixel_losses.mean()
            print(loss_ce)

        LS_loss = LS(semantic_output, semantic_label)
        total_loss = loss_ce +  LS_loss.mean()
        # print(total_loss)

        optimizer.zero_grad()
        scaler.scale(total_loss).backward()
        scaler.step(optimizer)
        scaler.update()




