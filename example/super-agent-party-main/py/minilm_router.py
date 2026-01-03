import onnxruntime as ort
from transformers import BertTokenizerFast
import numpy as np
import os
import threading
from typing import List, Union, Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import asyncio
import time

from py.get_setting import DEFAULT_EBD_DIR

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
MODEL_PATH = os.path.join(DEFAULT_EBD_DIR, MODEL_NAME)

# ---------- MiniLM ONNX Predictor ----------
class MiniLMOnnxPredictor:
    def __init__(self, model_dir: str, use_gpu: bool = False):
        self.model_dir = model_dir
        self.is_loaded = False
        if not self._check_files_exist():
            return
        try:
            self.tokenizer = BertTokenizerFast.from_pretrained(model_dir)
            providers = (["CUDAExecutionProvider", "CPUExecutionProvider"]
                         if use_gpu else ["CPUExecutionProvider"])
            model_path = (os.path.join(model_dir, "model_O4.onnx")
                          if os.path.exists(os.path.join(model_dir, "model_O4.onnx"))
                          else os.path.join(model_dir, "model.onnx"))
            if not os.path.exists(model_path):
                raise FileNotFoundError(model_path)
            self.session = ort.InferenceSession(model_path, providers=providers)
            self.input_names = [i.name for i in self.session.get_inputs()]
            print(f"MiniLM ONNX Predictor loaded from: {model_path}")
            self.is_loaded = True
        except Exception as e:
            print(f"Error loading MiniLM ONNX Predictor: {e}")
            self.is_loaded = False

    def _check_files_exist(self) -> bool:
        onnx_ok = os.path.exists(os.path.join(self.model_dir, "model_O4.onnx")) or \
                  os.path.exists(os.path.join(self.model_dir, "model.onnx"))
        tok_ok  = os.path.exists(os.path.join(self.model_dir, "tokenizer.json")) or \
                  os.path.exists(os.path.join(self.model_dir, "vocab.txt"))
        return onnx_ok and tok_ok

    def mean_pooling(self, model_output: np.ndarray, attention_mask: np.ndarray) -> np.ndarray:
        token_embeddings = model_output
        mask = np.expand_dims(attention_mask, -1).astype(float)
        mask = np.broadcast_to(mask, token_embeddings.shape)
        return np.sum(token_embeddings * mask, axis=1) / np.clip(mask.sum(axis=1), a_min=1e-9, a_max=None)

    def normalize(self, v: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(v, axis=1, keepdims=True)
        return v / np.clip(norm, a_min=1e-9, a_max=None)

    def predict(self, sentences: List[str]) -> np.ndarray:
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Cannot run prediction.")
        inputs = self.tokenizer(sentences, padding=True, truncation=True, max_length=512, return_tensors="np")
        ort_inputs = {"input_ids": inputs["input_ids"].astype(np.int64),
                      "attention_mask": inputs["attention_mask"].astype(np.int64)}
        if "token_type_ids" in self.input_names:
            tti = inputs.get("token_type_ids")
            ort_inputs["token_type_ids"] = (tti.astype(np.int64) if tti is not None else
                                            np.zeros_like(inputs["input_ids"], dtype=np.int64))
        outputs = self.session.run(None, ort_inputs)
        embeddings = self.mean_pooling(outputs[0], inputs["attention_mask"])
        return self.normalize(embeddings).astype(np.float32)

# ---------- 带热重载的池子 ----------
class MiniLMPool:
    def __init__(self, model_dir: str, use_gpu: bool = False):
        self.model_dir = model_dir
        self.use_gpu   = use_gpu
        self._predictor: Optional[MiniLMOnnxPredictor] = None
        self._lock     = threading.Lock()

    def _really_load(self) -> MiniLMOnnxPredictor:
        return MiniLMOnnxPredictor(self.model_dir, self.use_gpu)

    def get(self) -> MiniLMOnnxPredictor:
        if self._predictor and self._predictor.is_loaded:
            return self._predictor
        with self._lock:
            if self._predictor and self._predictor.is_loaded:
                return self._predictor
            if not MiniLMOnnxPredictor(model_dir=self.model_dir)._check_files_exist():
                raise RuntimeError("Model files not found")
            self._predictor = self._really_load()
            if not self._predictor.is_loaded:
                raise RuntimeError("Model failed to load")
            return self._predictor

minilm_pool = MiniLMPool(MODEL_PATH, use_gpu=False)

# ---------- FastAPI 数据模型 ----------
router = APIRouter(prefix="/minilm", tags=["MiniLM Embeddings (OpenAI Compatible)"])

class EmbeddingRequest(BaseModel):
    input: Union[str, List[str]]
    model: str = MODEL_NAME

class EmbeddingData(BaseModel):
    object: str = "embedding"
    embedding: List[float]
    index: int

class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: List[EmbeddingData]
    model: str
    usage: Dict[str, Any]

# ---------- 依赖 ----------
def get_minilm_predictor() -> MiniLMOnnxPredictor:
    try:
        return minilm_pool.get()
    except RuntimeError as e:
        raise HTTPException(status_code=503,
                            detail=f"Model '{MODEL_NAME}' is not installed or failed to load. ({e})")

# ---------- 嵌入接口 ----------
@router.post("/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(request: EmbeddingRequest,
                            predictor: MiniLMOnnxPredictor = Depends(get_minilm_predictor)):
    start = time.time()
    texts = [request.input] if isinstance(request.input, str) else request.input
    num_tokens = sum(len(predictor.tokenizer.tokenize(t)) for t in texts)
    try:
        embs = await asyncio.to_thread(predictor.predict, texts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {e}")
    data = [EmbeddingData(embedding=emb.tolist(), index=i) for i, emb in enumerate(embs)]
    return EmbeddingResponse(model=request.model,
                             data=data,
                             usage={"prompt_tokens": num_tokens,
                                    "total_tokens": num_tokens,
                                    "inference_time_ms": int((time.time() - start) * 1000)})

# ---------- 强制重载接口 ----------
@router.post("/reload")
async def reload_model():
    with minilm_pool._lock:
        minilm_pool._predictor = None
    return {"msg": "reload triggered, next request will load model"}