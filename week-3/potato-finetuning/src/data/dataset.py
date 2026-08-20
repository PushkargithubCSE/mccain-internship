"""
PyTorch Dataset for potato defect classification.
Loads images and labels from CSV splits.
"""
import os
import pandas as pd
from PIL import Image
import torch
from torch.utils.data import Dataset


class PotatoDataset(Dataset):
    """
    PyTorch Dataset for potato defect images.
    
    Args:
        csv_path (str): Path to train.csv / val.csv / test.csv
        transform (callable, optional): Transforms to apply to images
    """
    
    def __init__(self, csv_path, transform=None):
        """
        Args:
            csv_path: path to train/val/test CSV with columns:
                      [filename, path, class, class_id]
            transform: torchvision.transforms composition
        """
        self.df = pd.read_csv(csv_path)
        self.transform = transform
        
        # Create class to ID mapping
        self.classes = sorted(self.df['class'].unique())
        self.class_to_id = {c: i for i, c in enumerate(self.classes)}
        self.id_to_class = {i: c for c, i in self.class_to_id.items()}
        
    def __len__(self):
        """Return total number of samples."""
        return len(self.df)
    
    def __getitem__(self, idx):
        """
        Return (image, label) pair at index idx.
        
        Args:
            idx (int): Index of sample
            
        Returns:
            tuple: (image_tensor, label_id)
        """
        row = self.df.iloc[idx]
        
        # Load image
        img_path = row['path']
        img = Image.open(img_path).convert('RGB')
        
        # Apply transforms if provided
        if self.transform:
            img = self.transform(img)
        
        # Get label as class ID
        label = self.class_to_id[row['class']]
        
        return img, label
    
    def get_class_name(self, label_id):
        """Convert label ID back to class name."""
        return self.id_to_class[label_id]
    
    def get_class_weights(self):
        """
        Compute class weights for imbalanced datasets.
        Useful for weighted loss functions.
        
        Returns:
            torch.Tensor: weights for each class
        """
        class_counts = self.df['class'].value_counts().sort_index()
        class_counts = class_counts[[c for c in self.classes]]
        
        # Inverse frequency weighting
        weights = 1.0 / torch.tensor(class_counts.values, dtype=torch.float32)
        weights = weights / weights.sum() * len(self.classes)
        
        return weights