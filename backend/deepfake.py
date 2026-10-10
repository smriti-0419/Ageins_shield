"""Deepfake / AI-manipulation scanner (add-on for the Phishing Guard backend).

Photos : a pre-trained Vision Transformer scores the image (and the largest face in it),
         plus metadata checks for AI-generator fingerprints.
Videos : ~16 frames are sampled, each is scored the same way, and the scores are combined.

Honest limits: the result is a statistical estimate from a model trained on one dataset.
It can be wrong, especially on new AI generators and on small or heavily compressed media.
Audio (voice cloning) is not analysed. Never treat the score as proof about a person.
"""
import io
import os
import tempfile
import threading
from statistics import mean

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from PIL import Image, ImageOps
from starlette.concurrency import run_in_threadpool

# Swap the model without editing code: set DEEPFAKE_MODEL in backend/.env
MODEL_ID = os.getenv("DEEPFAKE_MODEL", "prithivMLmods/Deep-Fake-Detector-v2-Model")
FAKE_HINTS = tuple(
    h.strip().lower()
    for h in os.getenv("DEEPFAKE_FAKE_LABELS", "fake,deepfake,synthetic,generated,artificial").split(",")
)
MAX_IMAGE_MB = 10
MAX_VIDEO_MB = 50
VIDEO_FRAMES = 16
AI_MARKERS = (
    "midjourney", "stable diffusion", "dall-e", "dalle", "firefly", "comfyui",
    "automatic1111", "novelai", "leonardo.ai", "invokeai", "sdxl",
)

router = APIRouter(prefix="/api", tags=["deepfake"])
_clf = None
_clf_lock = threading.Lock()
_face_cascade = None


# ----------------------------------------------------------------- model
def _classifier():
    """Load the model on first use so the server still starts fast."""
    global _clf
    if _clf is None:
        with _clf_lock:
            if _clf is None:
                try:
                    import torch
                    from transformers import pipeline
                except ImportError as exc:
                    raise HTTPException(503, "Model packages are missing. Run: pip install torch transformers") from exc
                try:
                    _clf = pipeline("image-classification", model=MODEL_ID,
                                    device=0 if torch.cuda.is_available() else -1)
                except Exception as exc:  # noqa: BLE001
                    raise HTTPException(
                        503,
                        f"Could not load model '{MODEL_ID}'. Check your internet connection "
                        "(the first run downloads about 350 MB).",
                    ) from exc
    return _clf


def _fake_probability(image: Image.Image) -> float:
    results = _classifier()(image)
    labels = [r["label"] for r in results]
    is_fake = [any(h in l.lower() for h in FAKE_HINTS) for l in labels]
    if not any(is_fake):
        raise HTTPException(500, "Model labels not recognised: " + ", ".join(labels) +
                            ". Set DEEPFAKE_FAKE_LABELS in .env.")
    total = sum(r["score"] for r in results) or 1.0
    return sum(r["score"] for r, f in zip(results, is_fake) if f) / total


# ----------------------------------------------------------------- helpers
def _crop_face(rgb: np.ndarray):
    """Largest face with a margin, or None. Face-swap detectors work best on face crops."""
    global _face_cascade
    if not hasattr(cv2, "CascadeClassifier"):
        return None  # OpenCV 5 removed it. Use: pip install "opencv-python-headless==4.10.0.84"
    if _face_cascade is None:
        _face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    faces = _face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    if len(faces) == 0:
        return None
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    m = int(0.25 * max(w, h))
    y0, y1 = max(0, y - m), min(rgb.shape[0], y + h + m)
    x0, x1 = max(0, x - m), min(rgb.shape[1], x + w + m)
    return rgb[y0:y1, x0:x1]


def _verdict(score: int) -> str:
    return "Likely authentic" if score < 35 else "Inconclusive" if score < 65 else "Likely manipulated"


def _shrink(rgb: np.ndarray, longest=1280) -> np.ndarray:
    h, w = rgb.shape[:2]
    if max(h, w) <= longest:
        return rgb
    s = longest / max(h, w)
    return cv2.resize(rgb, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)


def _read(file: UploadFile, limit_mb: int) -> bytes:
    data = file.file.read(limit_mb * 1024 * 1024 + 1)
    if len(data) > limit_mb * 1024 * 1024:
        raise HTTPException(413, f"File is too large (limit {limit_mb} MB).")
    if not data:
        raise HTTPException(422, "The uploaded file is empty.")
    return data


def _sig(severity, title, detail):
    return {"severity": severity, "title": title, "detail": detail}


NOTE = ("This is an estimate from a machine-learning model, not proof. New AI generators, "
        "compression and low resolution can fool it. Audio is not analysed.")


async def _optional_user(request: Request):
    # Resolve the app's normal session logic at request time to avoid an import cycle.
    from server import optional_user
    return await optional_user(request)


# ----------------------------------------------------------------- images
def _metadata_signals(data: bytes, img: Image.Image):
    signals, ai_found = [], None
    texts = [str(v) for v in (img.info or {}).values() if isinstance(v, str)]
    exif = img.getexif()
    if exif.get(0x0131):  # Software tag
        texts.append(str(exif.get(0x0131)))
    blob = " ".join(texts).lower()
    for marker in AI_MARKERS:
        if marker in blob:
            ai_found = marker
            break
    if not ai_found and "sampler:" in blob and "steps:" in blob:
        ai_found = "Stable Diffusion generation settings"
    head = data[:2_000_000]
    if not ai_found and b"trainedAlgorithmicMedia" in head:
        ai_found = "IPTC 'trainedAlgorithmicMedia' tag"
    if ai_found:
        signals.append(_sig("bad", "AI-generator fingerprint in the file", f"Metadata mentions: {ai_found}."))
    if b"c2pa" in head.lower() or b"contentcredentials" in head.lower():
        signals.append(_sig("info", "Content Credentials (C2PA) present",
                            "The file carries provenance data. This tool does not verify its signature."))
    camera = exif.get(0x010F) or exif.get(0x0110)
    if camera:
        signals.append(_sig("info", "Camera metadata present",
                            f"Recorded device: {camera}. Metadata can be edited, so this is only a hint."))
    elif not ai_found:
        signals.append(_sig("info", "No camera metadata",
                            "Common for screenshots and social-media downloads. Not proof of anything."))
    return signals, bool(ai_found)


def _analyse_image(data: bytes):
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(422, "That file isn't a readable image.") from exc

    signals, ai_marker = _metadata_signals(data, img)
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((1600, 1600))
    rgb = np.array(img)

    face = _crop_face(rgb)
    p = _fake_probability(Image.fromarray(face if face is not None else rgb))
    if face is not None:
        p = max(p, _fake_probability(Image.fromarray(rgb)))
        signals.insert(0, _sig("info", "Face found", "The face and the whole image were both checked."))
    else:
        signals.insert(0, _sig("warn", "No face found",
                               "The model is tuned for faces, so the result is less reliable for this image."))

    score = round(p * 100)
    verdict = _verdict(score)
    if ai_marker:
        score, verdict = max(score, 95), "Likely AI-generated"
    return {"kind": "image", "score": score, "verdict": verdict, "signals": signals,
            "frames": [], "model": MODEL_ID, "note": NOTE}


# ----------------------------------------------------------------- video
def _sample_frames(cap):
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = cap.get(cv2.CAP_PROP_FPS) or 0

    def grab():
        ok, frame = cap.read()
        return _shrink(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)) if ok else None

    out = []
    if total > 0:
        for idx in np.unique(np.linspace(0, total - 1, VIDEO_FRAMES).astype(int)):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
            rgb = grab()
            if rgb is not None:
                out.append((idx / fps if fps else float(idx), rgb))
    if not out:  # length unknown (some WebM files): read in order and keep every 15th frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        keep, i = [], 0
        while i < 900:
            rgb = grab()
            if rgb is None:
                break
            if i % 15 == 0:
                keep.append((i / fps if fps else float(i), rgb))
            i += 1
        if keep:
            pick = np.unique(np.linspace(0, len(keep) - 1, min(VIDEO_FRAMES, len(keep))).astype(int))
            out = [keep[j] for j in pick]
    return out


def _analyse_video(data: bytes):
    path, cap = None, None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(data)
            path = tmp.name
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            raise HTTPException(422, "That file isn't a readable video.")
        frames = _sample_frames(cap)
    finally:
        if cap is not None:
            cap.release()
        if path and os.path.exists(path):
            os.remove(path)  # the upload is never kept
    if not frames:
        raise HTTPException(422, "No frames could be read from that video.")

    results, faces = [], 0
    for t, rgb in frames:
        face = _crop_face(rgb)
        faces += face is not None
        p = _fake_probability(Image.fromarray(face if face is not None else rgb))
        results.append({"t": round(t, 1), "score": round(p * 100), "face": face is not None})

    scores = sorted((r["score"] for r in results), reverse=True)
    score = round(mean(scores[: max(1, len(scores) // 2)]))  # mean of the highest half
    flagged = sum(r["score"] >= 65 for r in results)

    signals = [_sig("bad" if flagged > len(results) / 2 else "warn" if flagged else "info",
                    f"{flagged} of {len(results)} frames flagged",
                    "Frames scoring 65 or more are counted as suspicious.")]
    if faces == 0:
        signals.append(_sig("warn", "No faces found",
                            "The model is tuned for faces, so the result is less reliable for this video."))
    else:
        signals.append(_sig("info", f"Faces found in {faces} of {len(results)} frames",
                            "Face crops were scored where a face was detected."))
    if len(results) < 4:
        signals.append(_sig("warn", "Very few frames", "Short or unusual video; treat the result with extra caution."))
    return {"kind": "video", "score": score, "verdict": _verdict(score), "signals": signals,
            "frames": results, "model": MODEL_ID, "note": NOTE}


# ----------------------------------------------------------------- routes
@router.post("/scan/media")
async def scan_media(file: UploadFile = File(...), user=Depends(_optional_user)):
    """Run model work in a worker thread, then save scan metadata for signed-in users."""
    ctype = (file.content_type or "").lower()
    if ctype.startswith("image/"):
        result = await run_in_threadpool(_analyse_image, _read(file, MAX_IMAGE_MB))
    elif ctype.startswith("video/"):
        result = await run_in_threadpool(_analyse_video, _read(file, MAX_VIDEO_MB))
    else:
        raise HTTPException(415, "Upload a photo (JPG, PNG, WebP) or a video (MP4, MOV, WebM).")

    if user:
        from server import save_scan
        level = "danger" if result["score"] >= 65 else "moderate" if result["score"] >= 35 else "safe"
        result["scan_id"] = await save_scan(
            user, "deepfake", file.filename or result["kind"], result["score"], level,
            result["verdict"], dict(result),
        )
    return result


@router.get("/deepfake/status")
def deepfake_status():
    return {"model": MODEL_ID, "loaded": _clf is not None,
            "limits_mb": {"image": MAX_IMAGE_MB, "video": MAX_VIDEO_MB}}
