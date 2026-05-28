import torch
import torch.nn as nn
from torchvision import models, transforms

def get_img_transformer():

    transform = transforms.Compose([
        transforms.Resize((224, 224)),   # 모델 입력 크기에 맞게 수정
        transforms.ToTensor(),           # PIL -> Tensor, [0,255] -> [0,1]
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])
    return transform

def resnet_classifier(weights_path, device, num_classes=50):

    model = models.resnet34(weights=None)
    model.fc = nn.Linear(model.fc.in_features, num_classes)

    model.load_state_dict(torch.load(weights_path)['model'])
    model.to(device)
    model.eval()

    return model

if __name__ == "__main__":
    print('hi')