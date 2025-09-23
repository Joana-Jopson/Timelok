# face_rec/face_utils.py
import cv2
import torch
import numpy as np
from PIL import Image
from facenet_pytorch import InceptionResnetV1, MTCNN

# Initialize face detector and FaceNet model
mtcnn = MTCNN(image_size=160, margin=0)
resnet = InceptionResnetV1(pretrained='vggface2').eval()

def capture_webcam_image():
    """Captures a single image from webcam."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not access the webcam.")

    print("Capturing image... Press 'Space' to capture.")
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        cv2.imshow("Press Space to Capture", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 32:  # Space bar
            img = frame
            break

    cap.release()
    cv2.destroyAllWindows()
    return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))


def get_embedding(img):
    """Converts a face image to a 512-dim embedding using FaceNet."""
    face = mtcnn(img)
    if face is None:
        raise ValueError("No face detected.")
    with torch.no_grad():
        embedding = resnet(face.unsqueeze(0))
    return embedding


def compare_faces(known_embedding, unknown_embedding, threshold=0.85):
    """Compares two embeddings and returns whether they match."""
    dist = (known_embedding - unknown_embedding).norm().item()
    return dist < threshold
