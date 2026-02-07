# step03_crnn.py
"""
CRNN line recognizer (PyTorch).
- Minimal CRNN architecture (CNN + BiLSTM + CTC)
- Load a checkpoint with matching state_dict
- predict_line(np_image) -> string

Note: This is a wrapper. If you already have a CRNN repo, replace the Model class with your model
or load its checkpoint with matching model code/weights.
"""

import torch
import torch.nn as nn
import torchvision.transforms as transforms
import numpy as np
import cv2
from typing import List

# ------------- Alphabet / mapping -------------
# Define the alphabet your model was trained on.
# Include space and common punctuation used on invoices.
ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-/*().: ,+%#"
# CTC requires a blank token; we map indices accordingly (blank index = 0)
# We'll build char -> index & index -> char
CHARACTERS = list(ALPHABET)
BLANK_IDX = 0
IDX_TO_CHAR = {i+1: c for i, c in enumerate(CHARACTERS)}  # 1..N
# index 0 reserved for CTC blank

def ctc_greedy_decoder(preds):
    """
    preds: Tensor (T, C) logits (after softmax or raw logits)
    returns: decoded string (simple greedy, collapse repeated + remove blanks)
    """
    pred_idx = preds.argmax(axis=1).cpu().numpy().tolist()
    # collapse repeats and remove blank (0)
    output = []
    prev = None
    for p in pred_idx:
        if p != prev and p != BLANK_IDX:
            if p in IDX_TO_CHAR:
                output.append(IDX_TO_CHAR[p])
        prev = p
    return "".join(output)

# ------------- Minimal CRNN -------------
class BidirectionalLSTM(nn.Module):
    def __init__(self, nIn, nHidden, nOut):
        super(BidirectionalLSTM, self).__init__()
        self.rnn = nn.LSTM(nIn, nHidden, bidirectional=True, num_layers=1, batch_first=True)
        self.embedding = nn.Linear(nHidden*2, nOut)

    def forward(self, input_):
        recurrent, _ = self.rnn(input_)  # (b, seq, hidden*2)
        T, M, H = recurrent.size(0), recurrent.size(1), recurrent.size(2)
        t_rec = recurrent.contiguous()
        output = self.embedding(t_rec)
        return output  # (b, seq, nOut)

class CRNN(nn.Module):
    def __init__(self, imgH=32, nc=1, nclass=len(CHARACTERS)+1, nh=256):
        super(CRNN, self).__init__()
        assert imgH % 16 == 0, "imgH must be multiple of 16"
        self.cnn = nn.Sequential(
            # conv layers
            nn.Conv2d(nc, 64, 3, 1, 1), nn.ReLU(True), nn.MaxPool2d(2,2), # H/2
            nn.Conv2d(64,128,3,1,1), nn.ReLU(True), nn.MaxPool2d(2,2),      # H/4
            nn.Conv2d(128,256,3,1,1), nn.ReLU(True),
            nn.Conv2d(256,256,3,1,1), nn.ReLU(True), nn.MaxPool2d((2,1),(2,1)), # H/8
            nn.Conv2d(256,512,3,1,1), nn.ReLU(True), nn.BatchNorm2d(512),
            nn.Conv2d(512,512,3,1,1), nn.ReLU(True), nn.MaxPool2d((2,1),(2,1)), # H/16
            nn.Conv2d(512,512,2,1,0), nn.ReLU(True)
        )
        self.rnn = BidirectionalLSTM(512, nh, nclass)

    def forward(self, x):
        # x: (b, c, h, w)
        conv = self.cnn(x)
        b, c, h, w = conv.size()
        assert h == 1 or h == 2, "unexpected height after conv: {}".format(h)
        conv = conv.squeeze(2)  # (b, c, w)
        conv = conv.permute(0,2,1)  # (b, w, c) -> sequence length = w
        output = self.rnn(conv)  # (b, w, nclass)
        return output

# ------------- Recognizer wrapper -------------
class CRNNLineRecognizer:
    def __init__(self, checkpoint_path: str = None, device: str = None, imgH: int = 32):
        """
        checkpoint_path: path to your model .pth or .pt (state_dict or full model)
        device: 'cpu' or 'cuda'
        """
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.imgH = imgH
        self.model = CRNN(imgH=imgH).to(self.device)
        if checkpoint_path:
            self.load_checkpoint(checkpoint_path)
        else:
            raise RuntimeError("Please provide checkpoint_path to load pretrained CRNN weights.")

        # normalization transform: convert to tensor, normalize to [-1,1]
        self.transform = transforms.Compose([
            transforms.ToTensor(),  # to float tensor 0..1
            transforms.Normalize((0.5,), (0.5,))
        ])

    def load_checkpoint(self, path):
        ckpt = torch.load(path, map_location=self.device)
        if isinstance(ckpt, dict) and 'state_dict' in ckpt:
            state = ckpt['state_dict']
        else:
            state = ckpt
        # support optional key prefixes
        new_state = {}
        for k, v in state.items():
            name = k
            if name.startswith('module.'):
                name = name[7:]
            new_state[name] = v
        self.model.load_state_dict(new_state)
        self.model.eval()

    def preprocess_line(self, img):
        """
        img: numpy array (BGR or grayscale)
        returns Tensor shape (1,1,H,W) ready for model
        """
        if isinstance(img, str):
            img = cv2.imread(img)
        if img is None:
            raise ValueError("Empty image")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim==3 else img
        h, w = gray.shape
        # resize to target height, keep aspect ratio
        new_h = self.imgH
        new_w = max(8, int(float(w) * (new_h / float(h))))
        resized = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        # normalize to [0,1] and invert (so text dark/white consistent with training)
        resized = resized.astype(np.float32) / 255.0
        # expand dims (C=1)
        tensor = torch.from_numpy(resized).unsqueeze(0).unsqueeze(0)  # (1,1,H,W)
        tensor = (tensor - 0.5) / 0.5  # normalize to [-1,1]
        return tensor.to(self.device)

    def recognize_line(self, img):
        """
        img: numpy array (line crop)
        returns: recognized string (greedy CTC)
        """
        x = self.preprocess_line(img)
        with torch.no_grad():
            preds = self.model(x)  # (b, w, nclass)
            # take first batch
            preds = preds[0]  # (w, nclass)
            # optionally apply softmax for probability space (not necessary for argmax)
            probs = torch.softmax(preds, dim=1)
            text = ctc_greedy_decoder(probs)
        return text

    def recognize_lines(self, imgs: List):
        return [self.recognize_line(im) for im in imgs]

# ----------------- Quick test -----------------
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python step03_crnn.py <checkpoint.pth> <line_image.png>")
    else:
        ckpt = sys.argv[1]; imgp = sys.argv[2]
        r = CRNNLineRecognizer(ckpt)
        print("Text:", r.recognize_line(imgp))
