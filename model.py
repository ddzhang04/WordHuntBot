"""CNN letter recognition model for Word Hunt cells."""

import string
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset

MODEL_PATH = Path(__file__).parent / "model.pth"
DATASET_DIR = Path(__file__).parent / "dataset"
IMG_SIZE = 32
NUM_CLASSES = 26
LETTERS = list(string.ascii_lowercase)


def preprocess_cell(img: np.ndarray) -> np.ndarray:
    """Preprocess a cell image for CNN input.

    Applies CLAHE contrast enhancement and Otsu thresholding.
    Returns a 32x32 float32 array normalized to [0, 1].
    """
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    # CLAHE for contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
    enhanced = clahe.apply(gray)

    # Otsu thresholding
    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    resized = cv2.resize(binary, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_AREA)
    return resized.astype(np.float32) / 255.0


class LetterCNN(nn.Module):
    """Simple CNN for single letter classification (26 classes)."""

    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 32, 3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, 3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.dropout1 = nn.Dropout(0.25)
        self.fc1 = nn.Linear(64 * 8 * 8, 128)
        self.dropout2 = nn.Dropout(0.5)
        self.fc2 = nn.Linear(128, NUM_CLASSES)

    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))  # 32x32 -> 16x16
        x = self.pool(F.relu(self.conv2(x)))  # 16x16 -> 8x8
        x = self.dropout1(x)
        x = x.view(x.size(0), -1)
        x = F.relu(self.fc1(x))
        x = self.dropout2(x)
        x = self.fc2(x)
        return x


def _augment(img: np.ndarray) -> np.ndarray:
    """Apply random augmentation to a preprocessed 32x32 image."""
    h, w = img.shape

    # Random rotation (-10 to 10 degrees)
    angle = np.random.uniform(-10, 10)
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    img = cv2.warpAffine(img, M, (w, h), borderValue=0)

    # Random scale (0.85 to 1.15)
    scale = np.random.uniform(0.85, 1.15)
    M = cv2.getRotationMatrix2D((w / 2, h / 2), 0, scale)
    img = cv2.warpAffine(img, M, (w, h), borderValue=0)

    # Random shift (-2 to 2 pixels)
    dx, dy = np.random.randint(-2, 3), np.random.randint(-2, 3)
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    img = cv2.warpAffine(img, M, (w, h), borderValue=0)

    # Random noise
    if np.random.random() < 0.3:
        noise = np.random.normal(0, 0.05, img.shape).astype(np.float32)
        img = np.clip(img + noise, 0, 1)

    return img


class LetterDataset(Dataset):
    """Dataset of labeled letter images from dataset/ directory."""

    def __init__(self, root: Path = DATASET_DIR, augment: bool = False, oversample: bool = False):
        self.samples: list[tuple[Path, int]] = []
        self.augment = augment

        # Collect samples per class
        class_samples: dict[int, list[Path]] = {}
        for i, letter in enumerate(LETTERS):
            letter_dir = root / letter
            if letter_dir.is_dir():
                paths = list(letter_dir.glob("*.png"))
                class_samples[i] = paths
                for img_path in paths:
                    self.samples.append((img_path, i))

        # Oversample minority classes to match the max class size
        if oversample and class_samples:
            max_count = max(len(v) for v in class_samples.values())
            for i, paths in class_samples.items():
                if len(paths) < max_count:
                    extra = np.random.choice(
                        [str(p) for p in paths],
                        size=max_count - len(paths),
                        replace=True,
                    )
                    for p in extra:
                        self.samples.append((Path(p), i))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        processed = preprocess_cell(img)
        if self.augment:
            processed = _augment(processed)
        tensor = torch.from_numpy(processed).unsqueeze(0)  # (1, 32, 32)
        return tensor, label


def train(epochs: int = 50, lr: float = 0.001, batch_size: int = 32) -> None:
    """Train the CNN on the labeled dataset."""
    dataset = LetterDataset(augment=True, oversample=True)
    if len(dataset) == 0:
        print("No training data found in dataset/ directory.")
        print("Use dataset.py to create labeled training data first.")
        return

    print(f"Training on {len(dataset)} samples (with augmentation + oversampling)...")
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    model = LetterCNN().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()

    for epoch in range(epochs):
        model.train()
        total_loss = 0
        correct = 0
        total = 0

        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * images.size(0)
            _, predicted = outputs.max(1)
            correct += predicted.eq(labels).sum().item()
            total += labels.size(0)

        avg_loss = total_loss / total
        accuracy = correct / total * 100
        print(f"Epoch {epoch + 1}/{epochs} — loss: {avg_loss:.4f}, accuracy: {accuracy:.1f}%")

    torch.save(model.state_dict(), MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")


def load_model(path: Path = MODEL_PATH) -> LetterCNN:
    """Load a trained model from disk."""
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    model = LetterCNN()
    model.load_state_dict(torch.load(path, map_location=device, weights_only=True))
    model.to(device)
    model.eval()
    return model


def predict_letter(model: LetterCNN, cell_img: np.ndarray) -> str:
    """Predict a single letter from a cell image."""
    device = next(model.parameters()).device
    processed = preprocess_cell(cell_img)
    tensor = torch.from_numpy(processed).unsqueeze(0).unsqueeze(0).to(device)  # (1, 1, 32, 32)
    with torch.no_grad():
        output = model(tensor)
        _, predicted = output.max(1)
    return LETTERS[predicted.item()]


def predict_board(model: LetterCNN, cell_images: list[np.ndarray]) -> list[list[str]]:
    """Predict all 16 letters and return as a 4x4 grid."""
    letters = [predict_letter(model, img) for img in cell_images]
    return [letters[i * 4 : (i + 1) * 4] for i in range(4)]


if __name__ == "__main__":
    train()
