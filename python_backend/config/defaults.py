"""Product defaults owned by the backend configuration boundary."""

DEFAULT_TTS_PROVIDER_ID = "driver.tts.edge"
DEFAULT_TTS_VOICE = "zh-CN-XiaoxiaoNeural"
DEFAULT_TTS_RATE = "+0%"
DEFAULT_TTS_PITCH = "+0Hz"

DEFAULT_LIVE2D_IDLE_MOTION_GROUP = "Idle"
DEFAULT_LIVE2D_TAP_MOTION_GROUP = "TapBody"
DEFAULT_LIVE2D_TAP_HIT_AREA = "Body"
DEFAULT_LIVE2D_IDLE_THRESHOLD_MS = 15_000
DEFAULT_LIVE2D_FIT_SCALE = 0.6
DEFAULT_LIVE2D_VERTICAL_POSITION_RATIO = 0.6
DEFAULT_LIVE2D_TIME_SCALE = 0.8
DEFAULT_LIVE2D_PARAMETER_IDS = {
    "eyeBlinkLeft": "ParamEyeLOpen",
    "eyeBlinkRight": "ParamEyeROpen",
    "mouthOpen": "ParamMouthOpenY",
    "headPan": "ParamAngleX",
    "headTilt": "ParamAngleY",
    "headRoll": "ParamAngleZ",
    "bodyPan": "ParamBodyAngleX",
}
