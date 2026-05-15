"""
CNN Model for multi-label genre classification on mel-spectrograms.

Architecture:
    Input: Mel-spectrogram (1 × 128 × 256)
    → Conv2D blocks (32 → 64 → 128 filters)
    → Global Average Pooling
    → Dense 256 (Embedding layer)
    → Dense N (Genre predictions with sigmoid)

The embedding layer (256-D vector) is used for similarity search.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
import numpy as np
from pathlib import Path


class ConvBlock(nn.Module):
    """A single convolutional block: Conv2D → BatchNorm → ReLU → MaxPool → Dropout."""
    
    def __init__(self, in_channels: int, out_channels: int, dropout: float = 0.3):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.pool = nn.MaxPool2d(2, 2)
        self.dropout = nn.Dropout2d(dropout)
    
    def forward(self, x):
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = self.pool(x)
        x = self.dropout(x)
        return x


class MusicCNN(nn.Module):
    """
    CNN for multi-label music genre classification.
    
    Args:
        n_classes: Number of genre classes.
        input_channels: Number of input channels (1 for mono spectrogram).
        conv_filters: List of filter counts for each conv block.
        embedding_dim: Size of the embedding vector.
        dropout: Dropout rate.
    """
    
    def __init__(
        self,
        n_classes: int = 10,
        input_channels: int = 1,
        conv_filters: list = None,
        embedding_dim: int = 256,
        dropout: float = 0.3,
    ):
        super().__init__()
        
        if conv_filters is None:
            conv_filters = [32, 64, 128]
        
        self.n_classes = n_classes
        self.embedding_dim = embedding_dim
        
        # Build conv blocks
        layers = []
        in_ch = input_channels
        for out_ch in conv_filters:
            layers.append(ConvBlock(in_ch, out_ch, dropout))
            in_ch = out_ch
        self.conv_blocks = nn.Sequential(*layers)
        
        # Global Average Pooling
        self.global_pool = nn.AdaptiveAvgPool2d(1)
        
        # Embedding layer
        self.embedding = nn.Sequential(
            nn.Linear(conv_filters[-1], embedding_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        
        # Classification head
        self.classifier = nn.Linear(embedding_dim, n_classes)
    
    def forward(self, x, return_embedding: bool = False):
        """
        Forward pass.
        
        Args:
            x: Input tensor (batch × 1 × height × width).
            return_embedding: If True, return embedding vector instead of class logits.
        
        Returns:
            If return_embedding: (batch × embedding_dim) tensor.
            Otherwise: (batch × n_classes) tensor of logits (use sigmoid for probabilities).
        """
        # Conv blocks
        x = self.conv_blocks(x)
        
        # Global average pooling → (batch, channels, 1, 1)
        x = self.global_pool(x)
        x = x.view(x.size(0), -1)  # (batch, channels)
        
        # Embedding
        emb = self.embedding(x)
        
        if return_embedding:
            return emb
        
        # Classifier
        logits = self.classifier(emb)
        return logits
    
    def get_embedding(self, x) -> np.ndarray:
        """
        Get embedding vector for input(s).
        
        Args:
            x: Input tensor.
        
        Returns:
            Numpy array of embeddings.
        """
        self.eval()
        with torch.no_grad():
            emb = self.forward(x, return_embedding=True)
        return emb.cpu().numpy()


class MusicResNet(nn.Module):
    """
    More complex CNN based on ResNet-18 architecture, adapted for 1-channel mel-spectrograms.
    """
    
    def __init__(
        self,
        n_classes: int = 10,
        embedding_dim: int = 256,
        dropout: float = 0.5,
    ):
        super().__init__()
        self.n_classes = n_classes
        self.embedding_dim = embedding_dim
        
        # Load base ResNet-18 (untrained, as audio spects are very different from ImageNet)
        self.resnet = models.resnet18(weights=None)
        
        # Replace the first conv layer to accept 1 channel instead of 3
        # Original: Conv2d(3, 64, kernel_size=(7, 7), stride=(2, 2), padding=(3, 3), bias=False)
        self.resnet.conv1 = nn.Conv2d(
            1, 64, kernel_size=7, stride=2, padding=3, bias=False
        )
        
        # We replace the final fully-connected layer (resnet.fc) with our embedding + classifier sequence
        num_ftrs = self.resnet.fc.in_features
        # We remove the original fc layer and inject an Identity layer so it just outputs the pooled features
        self.resnet.fc = nn.Identity()
        
        # Embedding block
        self.embedding = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(num_ftrs, embedding_dim),
            nn.BatchNorm1d(embedding_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        
        # Classification head
        self.classifier = nn.Linear(embedding_dim, n_classes)
        
    def forward(self, x, return_embedding: bool = False):
        # resnet outputs the feature vector of size (batch, num_ftrs) due to our Identity trick
        resnet_out = self.resnet(x)
        
        # Embedding
        emb = self.embedding(resnet_out)
        
        if return_embedding:
            return emb
            
        # Classifier
        logits = self.classifier(emb)
        return logits
        
    def get_embedding(self, x) -> np.ndarray:
        self.eval()
        with torch.no_grad():
            emb = self.forward(x, return_embedding=True)
        return emb.cpu().numpy()


class MusicMLP(nn.Module):
    """
    MLP baseline model for genre classification on hand-crafted features.
    
    Args:
        n_features: Number of input features.
        n_classes: Number of genre classes.
        hidden_dims: List of hidden layer sizes.
        dropout: Dropout rate.
    """
    
    def __init__(
        self,
        n_features: int = 200,
        n_classes: int = 10,
        hidden_dims: list = None,
        embedding_dim: int = 128,
        dropout: float = 0.3,
    ):
        super().__init__()
        
        if hidden_dims is None:
            hidden_dims = [512, 256]
        
        self.n_classes = n_classes
        self.embedding_dim = embedding_dim
        
        # Build hidden layers
        layers = []
        in_dim = n_features
        for h_dim in hidden_dims:
            layers.extend([
                nn.Linear(in_dim, h_dim),
                nn.BatchNorm1d(h_dim),
                nn.ReLU(),
                nn.Dropout(dropout),
            ])
            in_dim = h_dim
        self.hidden = nn.Sequential(*layers)
        
        # Embedding layer
        self.embedding = nn.Sequential(
            nn.Linear(in_dim, embedding_dim),
            nn.ReLU(),
        )
        
        # Classifier
        self.classifier = nn.Linear(embedding_dim, n_classes)
    
    def forward(self, x, return_embedding: bool = False):
        x = self.hidden(x)
        emb = self.embedding(x)
        
        if return_embedding:
            return emb
        
        logits = self.classifier(emb)
        return logits
    
    def get_embedding(self, x) -> np.ndarray:
        self.eval()
        with torch.no_grad():
            emb = self.forward(x, return_embedding=True)
        return emb.cpu().numpy()
