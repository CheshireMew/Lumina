import json
import os
import wave
import pyaudio
import sherpa_onnx
import numpy as np
import soundfile as sf

asr_model_path = "data/model/ASR/sherpa-onnx-sense-voice-zh-en-ja-ko-yue"
vp_model_path = "data/model/SpeakerID/3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx"
vp_config, extractor, audio1, sample_rate1, embedding1 = None, None, None, None, None
with open('data/db/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
asr_sensitivity = config["语音识别灵敏度"]
voiceprint_switch = config["声纹识别"]
with open('data/set/more_set.json', 'r', encoding='utf-8') as f:
    more_set = json.load(f)
mic_num = int(more_set["麦克风编号"])
voiceprint_threshold = float(more_set["声纹识别阈值"])
SILENCE_DURATION_MAP = {"高": 1, "中": 2, "低": 3}
SILENCE_DURATION = SILENCE_DURATION_MAP.get(asr_sensitivity, 3)
FORMAT = pyaudio.paInt16
CHANNELS, RATE, CHUNK = 1, 16000, 1024
SILENCE_CHUNKS = SILENCE_DURATION * RATE / CHUNK  # 静音持续的帧数
p, stream, recognizer = None, None, None
cache_path = "data/cache/cache_record.wav"
model = f"{asr_model_path}/model.int8.onnx"
tokens = f"{asr_model_path}/tokens.txt"


def rms(data):  # 计算音频数据的均方根
    return np.sqrt(np.mean(np.frombuffer(data, dtype=np.int16) ** 2))


def dbfs(rms_value):  # 将均方根转换为分贝满量程（dBFS）
    return 20 * np.log10(rms_value / (2 ** 15))  # 16位音频


def record_audio():  # 录音
    global p, stream
    frames = []
    recording = True
    silence_counter = 0  # 用于记录静音持续的帧数
    if p is None:
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK,
                        input_device_index=mic_num)
    while recording:
        data = stream.read(CHUNK)
        frames.append(data)
        current_rms = rms(data)
        current_dbfs = dbfs(current_rms)
        if str(current_dbfs) != "nan":
            silence_counter += 1  # 增加静音计数
            if silence_counter > SILENCE_CHUNKS:  # 判断是否达到设定的静音持续时间
                recording = False
        else:
            silence_counter = 0  # 重置静音计数
    return b''.join(frames)


# open_source_project_address:https://github.com/swordswind/ai_virtual_mate_web
def verify_speakers():  # 声纹识别
    global vp_config, extractor, audio1, sample_rate1, embedding1
    audio_file1 = "data/cache/voiceprint/myvoice.wav"
    audio_file2 = cache_path

    def load_audio(filename):
        audio, sample_rate = sf.read(filename, dtype="float32", always_2d=True)
        audio = audio[:, 0]
        return audio, sample_rate

    def extract_speaker_embedding(audio, sample_rate):
        vp_stream = extractor.create_stream()
        vp_stream.accept_waveform(sample_rate=sample_rate, waveform=audio)
        vp_stream.input_finished()
        embedding = extractor.compute(vp_stream)
        return np.array(embedding)

    def cosine_similarity():
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        return dot_product / (norm1 * norm2) if (norm1 * norm2) != 0 else 0.0

    print("正在加载说话人嵌入模型...")
    try:
        if vp_config is None:
            vp_config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=vp_model_path, debug=False, provider="cpu",
                                                                    num_threads=int(os.cpu_count()) - 1)
            extractor = sherpa_onnx.SpeakerEmbeddingExtractor(vp_config)
            audio1, sample_rate1 = load_audio(audio_file1)
            embedding1 = extract_speaker_embedding(audio1, sample_rate1)
        audio2, sample_rate2 = load_audio(audio_file2)
        embedding2 = extract_speaker_embedding(audio2, sample_rate2)
        similarity = cosine_similarity()
        if similarity >= voiceprint_threshold:
            print(f"✓ 结果: 是同一个说话人 (相似度 {similarity:.4f} >= 阈值 {voiceprint_threshold})")
            return True
        else:
            print(f"✗ 结果: 不是同一个说话人 (相似度 {similarity:.4f} < 阈值 {voiceprint_threshold})")
            return False
    except Exception as e:
        print(f"声纹识别出错，详情：{e}")
        return True


def recognize_audio(audiodata):  # 语音识别
    global recognizer
    if recognizer is None:
        recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(model=model, tokens=tokens, use_itn=True,
                                                                    num_threads=int(os.cpu_count()) - 1)
    with wave.open(cache_path, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(audiodata)
    with wave.open(cache_path, 'rb') as wf:
        n_frames = wf.getnframes()
        duration = n_frames / RATE
    if duration < SILENCE_DURATION + 0.5:
        return ""
    if voiceprint_switch == "开启":
        if not verify_speakers():
            return ""
    audio, sample_rate = sf.read(cache_path, dtype="float32", always_2d=True)
    asr_stream = recognizer.create_stream()
    asr_stream.accept_waveform(sample_rate, audio[:, 0])
    recognizer.decode_stream(asr_stream)
    res = json.loads(str(asr_stream.result))
    emotion_key = res.get('emotion', '').strip('<|>')
    event_key = res.get('event', '').strip('<|>')
    text = res.get('text', '')
    emotion_dict = {"HAPPY": "[开心]", "SAD": "[伤心]", "ANGRY": "[愤怒]", "DISGUSTED": "[厌恶]", "SURPRISED": "[惊讶]",
                    "NEUTRAL": "", "EMO_UNKNOWN": ""}
    event_dict = {"BGM": "", "Applause": "[鼓掌]", "Laughter": "[大笑]", "Cry": "[哭]", "Sneeze": "[打喷嚏]",
                  "Cough": "[咳嗽]", "Breath": "[深呼吸]", "Speech": "", "Event_UNK": ""}
    emotion = emotion_dict.get(emotion_key, "")
    event = event_dict.get(event_key, "")
    result = event + text + emotion
    if result == "The.":
        return ""
    return result
