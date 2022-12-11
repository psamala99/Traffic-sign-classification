import numpy as np
import torch
from capsnet import CapsNet
# from tqdm import tqdm
from torchvision import transforms
from PIL import Image
import matplotlib.pyplot as plt
from lime import lime_image
import os
import random
from skimage.segmentation import mark_boundaries
from utils import download_data, download_model
from test_capsnet import Config
from lime.wrappers.scikit_image import SegmentationAlgorithm

torch.cuda.empty_cache()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
BATCH_SIZE = 16
N_EPOCHS = 2
LEARNING_RATE = 1e-4
MOMENTUM = 0.9
NUM_CLASSES = 43
torch.manual_seed(1)
torch.cuda.empty_cache()
code_dir = os.getcwd()
model_dir = os.path.join(os.path.split(code_dir)[0], 'Model')
data_dir = os.path.join(os.path.split(code_dir)[0], 'Data')


class Lime:
    def __init__(self):
        self.pil_transform = transforms.Compose([
            transforms.Resize((28, 28)),
        ])
        self.preprocess_transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
        ])
        self.capsnet_model = Lime.build_state()
        self.explainer = lime_image.LimeImageExplainer()
        self.segmenter = SegmentationAlgorithm('quickshift')

    @staticmethod
    def build_state():
        test_img_dir = os.path.join(data_dir, 'Test')
        if len(os.listdir(test_img_dir)) < 6:
            download_data(data_dir)
        if not os.path.exists(os.path.join(model_dir, 'capsnet-model.pt')):
            download_model(model_dir)
        capsnet_config = Config()
        model = CapsNet(capsnet_config)
        model.load_state_dict(torch.load(os.path.join(model_dir, 'capsnet-model.pt')))
        model.to(device)
        return model

    def batch_predict(self, images):
        self.capsnet_model.eval()
        batch = torch.stack(tuple(self.preprocess_transform(j) for j in images), dim=0)
        batch = batch.to(device)
        output, _, masked = self.capsnet_model(batch)
        return masked.data.cpu().numpy()

    def plot(self, image):
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(8, 4))
        ax1.imshow(image)
        ax1.set_title('Image')
        ax2.imshow(self.explanation.segments)
        ax2.set_title('Segments')

        temp, mask = self.explanation.get_image_and_mask(
            self.explanation.top_labels[0],
            positive_only=False,
            num_features=50,
            hide_rest=True
        )
        img_boundary2 = mark_boundaries(temp / 255.0, mask)
        ax3.imshow(img_boundary2)
        ax3.set_title('Image with Mask')
        plt.show()

    @staticmethod
    def get_image(path):
        with open(os.path.abspath(path), 'rb') as f:
            with Image.open(f) as image:
                return image.convert('RGB')

    def __call__(self, image):
        """
        Lime image explainer
        :param image:
        :return:
        """
        image = Lime.get_image(image)
        self.explanation = self.explainer.explain_instance(
            np.array(self.pil_transform(image)),
            self.batch_predict,  # classification function
            top_labels=5,
            segmentation_fn=self.segmenter,
            num_samples=1000,
        )  # number of images that will be sent to classification function
        self.plot(image)


if __name__ == '__main__':
    lime = Lime()
    for i in range(6):
        img_path = random.choice(os.listdir(os.path.join(data_dir, 'Test')))
        img = os.path.join(data_dir, 'Test', img_path)
        lime(img)
